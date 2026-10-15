"""NOVA data-sprawl governor (Fieldkit 2.0) -- write-side limits + aging plan.

Added 2026-10-07 (Grok Bot steward, Michael-requested). Config-driven, reversible.

  Config : data/config/governor.json   (missing file -> built-in DEFAULTS below)
  Log    : data/governor/governor_dryrun.jsonl  (size-capped, rotates to .1)

DEFAULT IS DRY-RUN. With "enforce": false (the default) every hook only LOGS what it
WOULD dedup / rate-limit / budget-block, and always lets the write through. Aging is
only ever a projection ("plan"). Nothing is skipped and nothing is deleted.

ENFORCEMENT (Michael's call, later): set "enforce": true in data/config/governor.json.
  - write hooks then skip duplicate / rate-limited / over-budget telemetry writes
  - `python -m nova.governor apply` then ages rows per plan: NOVA.db is backed up first,
    every removed row is exported to data/governor/cold/*.jsonl.gz (tiered demotion), then deleted.
To disable the governor entirely: "enabled": false.  To uninstall: restore *.bak-20261007* files.

Hooks never raise: any internal error -> allow the write (fail-open, function preserved).
"""
from __future__ import annotations

import calendar
import copy
import gzip
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "enforce": False,  # <-- THE enforcement flag. OFF by default.
    "log_max_bytes": 5_000_000,
    "budget": {"db_soft_mb": 256, "db_hard_mb": 1024},
    "facts": {
        "default_tier": "core",
        "core_dedup_window_s": 600,
        "telemetry_dedup_window_s": 86400,
        "classes": {
            "Ax-THERMAL": {"tier": "telemetry", "min_interval_s": 1800, "keep_last": 200, "ttl_days": 14},
            "Ax-HOLMES": {"tier": "telemetry", "min_interval_s": 3600, "keep_last": 200, "ttl_days": 14},
            "Ax-WATSON": {"tier": "telemetry", "min_interval_s": 3600, "keep_last": 200, "ttl_days": 14},
            "Tx-CRAWL": {"tier": "telemetry", "titles": ["metal-map", "sweep", "cycle", "needs", "thumb-scan"],
                         "min_interval_s": 3600, "keep_last": 200, "ttl_days": 14},
            "Tx-CAM*": {"tier": "telemetry", "min_interval_s": 1800, "keep_last": 300, "ttl_days": 14},
            "Ax-OLLAMA": {"tier": "telemetry", "min_interval_s": 0, "keep_last": 30, "ttl_days": 30},
            "Ax-HW": {"tier": "telemetry", "min_interval_s": 0, "keep_last": 50, "ttl_days": 30},
            "Tx-HW": {"tier": "telemetry", "min_interval_s": 0, "keep_last": 50, "ttl_days": 30},
            "Ax-RAG": {"tier": "telemetry", "min_interval_s": 0, "keep_last": 200, "ttl_days": 30},
            "Tx-HUNT-MISS": {"tier": "telemetry", "min_interval_s": 0, "keep_last": 200, "ttl_days": 30},
        },
        "keep_min": 20,
    },
    "observations": {"min_interval_s": 900, "dedup_window_s": 86400, "ttl_days": 14,
                     "keep_last_per_source": 2000, "keep_min_per_source": 200},
    "packets": {"dedup_window_s": 3600, "age_status": ["cleared", "logged", "delivered", "fail"], "ttl_days": 30},
    "chunks": {"dedup_hash": True, "age_status": ["cleared"], "ttl_days": 60},
    "master_log": {"ttl_days": 30},
    "bites": {"age_status": ["expired", "played"], "ttl_days": 7},
    "whi": {"max_packets_per_cycle": 25, "min_score": 60, "min_chars": 200, "max_chars": 7500,
            "require_citation": True, "reject_prompt_echo": True,
            "land_whi": "Tx-WHI", "promote_whi": "0x-WHI", "land_status": "temp"},
}

_CACHE: dict[str, Any] = {"t": 0.0, "mtime": None, "cfg": None, "size_t": 0.0, "size": 0}


def _home() -> Path:
    from nova import db
    return db.home()


def config_path() -> Path:
    return _home() / "data" / "config" / "governor.json"


def log_path() -> Path:
    return _home() / "data" / "governor" / "governor_dryrun.jsonl"


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict) and k != "classes":
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def config(force: bool = False) -> dict:
    now = time.time()
    if not force and _CACHE["cfg"] is not None and now - _CACHE["t"] < 10:
        return _CACHE["cfg"]
    p = config_path()
    try:
        mt = p.stat().st_mtime if p.is_file() else None
    except OSError:
        mt = None
    if force or _CACHE["cfg"] is None or mt != _CACHE["mtime"]:
        cfg = copy.deepcopy(DEFAULTS)
        if mt is not None:
            try:
                cfg = _merge(DEFAULTS, json.loads(p.read_text(encoding="utf-8-sig")))
            except Exception as exc:  # bad json -> safe defaults (dry-run)
                cfg = copy.deepcopy(DEFAULTS)
                cfg["_config_error"] = str(exc)
        _CACHE["cfg"], _CACHE["mtime"] = cfg, mt
    _CACHE["t"] = now
    return _CACHE["cfg"]


def enforcing(cfg: dict | None = None) -> bool:
    cfg = cfg or config()
    return bool(cfg.get("enabled", True)) and cfg.get("enforce") is True


def _zulu_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _epoch(z: str | None) -> float | None:
    if not z:
        return None
    try:
        return float(calendar.timegm(time.strptime(z[:19], "%Y-%m-%dT%H:%M:%S")))
    except Exception:
        return None


def _log(ev: dict) -> None:
    try:
        cfg = config()
        p = log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            if p.is_file() and p.stat().st_size > int(cfg.get("log_max_bytes", 5_000_000)):
                old = p.with_suffix(".jsonl.1")
                if old.exists():
                    old.unlink()
                p.rename(old)
        except OSError:
            pass
        ev = {"ts": _zulu_now(), "enforced": enforcing(cfg), **ev}
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=True)[:600] + "\n")
    except Exception:
        return


def db_size_mb() -> float:
    now = time.time()
    if now - _CACHE["size_t"] > 60:
        try:
            from nova import db
            _CACHE["size"] = os.path.getsize(db.db_path())
        except Exception:
            _CACHE["size"] = 0
        _CACHE["size_t"] = now
    return _CACHE["size"] / 1e6


def fact_rule(whi: str, title: str, cfg: dict | None = None) -> dict:
    """Return the class rule for (whi,title); tier 'core' when unlisted."""
    cfg = cfg or config()
    fc = cfg.get("facts", {})
    classes = fc.get("classes", {}) or {}
    rule = classes.get(whi)
    if rule is None:
        for k, v in classes.items():
            if k.endswith("*") and whi.startswith(k[:-1]):
                rule = v
                break
    if rule is None:
        return {"tier": fc.get("default_tier", "core")}
    titles = rule.get("titles")
    if titles and title not in titles:
        return {"tier": fc.get("default_tier", "core")}
    return rule


def decide_fact(whi: str, title: str, body: str, last: tuple | None, now_s: float,
                cfg: dict, size_mb: float = 0.0) -> str | None:
    """Pure decision (used by live hook and by replay). last=(zulu, body) of newest same whi+title."""
    fc = cfg.get("facts", {})
    rule = fact_rule(whi, title, cfg)
    tele = rule.get("tier") == "telemetry"
    if last:
        age = now_s - (_epoch(last[0]) or 0)
        win = fc.get("telemetry_dedup_window_s" if tele else "core_dedup_window_s", 600)
        if last[1] == body and age < win:
            return "dedup_exact"
        mi = int(rule.get("min_interval_s") or 0)
        if tele and mi and age < mi:
            return "rate_limit"
    if tele and size_mb > float(cfg.get("budget", {}).get("db_hard_mb", 1e9)):
        return "budget_hard"
    return None


def _hook_error(hook: str, exc: Exception, dry_value):
    """2.1 fail-closed: when enforcing, a hook that cannot decide DENIES the write.
    In dry-run (default) the write proceeds, but the error is logged so it is visible."""
    try:
        enf = enforcing()
    except Exception:
        enf = False
    _log({"table": "hook", "action": "hook_error", "hook": hook, "error": str(exc)[:160],
          "decision": "deny" if enf else "allow(dry-run)"})
    if enf and dry_value is True:
        return False
    return dry_value


def gate_fact(con, whi: str, title: str, body: str) -> bool:
    """put_fact hook. True = write it. Dry-run always returns True (logs WOULD-actions)."""
    try:
        cfg = config()
        if not cfg.get("enabled", True):
            return True
        row = con.execute("SELECT zulu, body FROM facts WHERE whi=? AND title=? ORDER BY id DESC LIMIT 1",
                          (whi, title)).fetchone()
        last = (row[0], row[1]) if row else None
        act = decide_fact(whi, title, body, last, time.time(), cfg, db_size_mb())
        if not act:
            return True
        _log({"table": "facts", "action": act, "whi": whi, "title": title[:60]})
        return not enforcing(cfg)
    except Exception as exc:
        return _hook_error("gate", exc, True)


def decide_obs(source: str, body: str, last: tuple | None, now_s: float, cfg: dict) -> str | None:
    oc = cfg.get("observations", {})
    if not last:
        return None
    age = now_s - (_epoch(last[0]) or 0)
    if last[1] == body and age < oc.get("dedup_window_s", 86400):
        return "dedup_exact"
    mi = int(oc.get("min_interval_s") or 0)
    if mi and age < mi:
        return "rate_limit"
    return None


def gate_obs(con, source: str, body: str) -> bool:
    try:
        cfg = config()
        if not cfg.get("enabled", True):
            return True
        row = con.execute("SELECT zulu, body FROM observations WHERE source=? ORDER BY id DESC LIMIT 1",
                          (source,)).fetchone()
        act = decide_obs(source, body, (row[0], row[1]) if row else None, time.time(), cfg)
        if not act:
            return True
        _log({"table": "observations", "action": act, "source": source[:40]})
        return not enforcing(cfg)
    except Exception as exc:
        return _hook_error("gate", exc, True)


def gate_packet(con, dest: str, kind: str, body: str) -> int | None:
    """post_packet hook. Returns existing packet id to reuse when an enforced skip happens, else None."""
    try:
        cfg = config()
        if not cfg.get("enabled", True):
            return None
        win = int(cfg.get("packets", {}).get("dedup_window_s", 3600))
        row = con.execute("SELECT id, zulu, body FROM packets WHERE dest=? AND kind=? ORDER BY id DESC LIMIT 1",
                          (dest, kind)).fetchone()
        if row and row[2] == body and time.time() - (_epoch(row[1]) or 0) < win:
            _log({"table": "packets", "action": "dedup_exact", "kind": kind, "dest": dest, "existing": row[0]})
            return int(row[0]) if enforcing(cfg) else None
        return None
    except Exception as exc:
        _hook_error("gate_reuse", exc, None)
        return None


def gate_chunk(con, hash_: str, cite: str = "") -> int | None:
    """chunk insert hook (ingest_pipe / crawl). Returns existing chunk id to reuse on enforced dedup."""
    try:
        cfg = config()
        if not cfg.get("enabled", True) or not cfg.get("chunks", {}).get("dedup_hash", True) or not hash_:
            return None
        row = con.execute("SELECT id, status FROM chunks WHERE hash=? AND status IN ('temp','live') ORDER BY id DESC LIMIT 1",
                          (hash_,)).fetchone()
        if row:
            _log({"table": "chunks", "action": "dedup_hash", "hash": hash_, "existing": row[0], "cite": cite[:80]})
            return int(row[0]) if enforcing(cfg) else None
        return None
    except Exception as exc:
        _hook_error("gate_reuse", exc, None)
        return None


# ---------------------------------------------------------------- aging plan (projection) / apply

def _cutoff(days: float, soft: bool) -> str:
    d = days * (0.5 if soft else 1.0)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - d * 86400))


def plan(con, cfg: dict | None = None) -> dict:
    """Projected removals per table. Read-only: SELECTs only."""
    cfg = cfg or config()
    soft = db_size_mb() > float(cfg["budget"].get("db_soft_mb", 1e9))
    out: dict[str, Any] = {"zulu": _zulu_now(), "db_mb": round(db_size_mb(), 2), "soft_budget_tightening": soft,
                           "tables": {}, "ids": {}}
    fc = cfg["facts"]
    whis = [r[0] for r in con.execute("SELECT DISTINCT whi FROM facts")]
    ids_f: list[int] = []
    by_class: dict[str, int] = {}
    for w in whis:
        rule = fact_rule(w, "", cfg) if not (fc["classes"].get(w) or {}).get("titles") else fc["classes"][w]
        if rule.get("tier") != "telemetry":
            continue
        titles = rule.get("titles")
        tclause, targs = "", []
        if titles:
            tclause = " AND title IN (%s)" % ",".join("?" * len(titles))
            targs = list(titles)
        cut = _cutoff(float(rule.get("ttl_days", 14)), soft)
        sql = ("SELECT id FROM (SELECT id, zulu, ROW_NUMBER() OVER (PARTITION BY whi, title ORDER BY id DESC) rn "
               f"FROM facts WHERE whi=?{tclause}) WHERE rn > ? AND (rn > ? OR zulu < ?)")
        got = [r[0] for r in con.execute(sql, [w, *targs, int(fc.get("keep_min", 20)), int(rule.get("keep_last", 200)), cut])]
        if got:
            by_class[w] = len(got)
            ids_f += got
    out["tables"]["facts"] = {"total": con.execute("SELECT COUNT(*) FROM facts").fetchone()[0],
                              "would_remove": len(ids_f), "by_class": by_class}
    out["ids"]["facts"] = ids_f
    oc = cfg["observations"]
    cut = _cutoff(float(oc["ttl_days"]), soft)
    ids_o = [r[0] for r in con.execute(
        "SELECT id FROM (SELECT id, zulu, ROW_NUMBER() OVER (PARTITION BY source ORDER BY id DESC) rn FROM observations) "
        "WHERE rn > ? AND (rn > ? OR zulu < ?)", (int(oc["keep_min_per_source"]), int(oc["keep_last_per_source"]), cut))]
    out["tables"]["observations"] = {"total": con.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
                                     "would_remove": len(ids_o)}
    out["ids"]["observations"] = ids_o
    for t in ("packets", "chunks", "bites"):
        tc = cfg[t]
        st = tc.get("age_status") or []
        if not st:
            continue
        cut = _cutoff(float(tc["ttl_days"]), soft)
        ids = [r[0] for r in con.execute(
            f"SELECT id FROM [{t}] WHERE status IN ({','.join('?' * len(st))}) AND zulu < ?", (*st, cut))]
        out["tables"][t] = {"total": con.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0], "would_remove": len(ids),
                            "statuses": st}
        out["ids"][t] = ids
    cut = _cutoff(float(cfg["master_log"]["ttl_days"]), soft)
    ids = [r[0] for r in con.execute("SELECT id FROM master_log WHERE zulu < ?", (cut,))]
    out["tables"]["master_log"] = {"total": con.execute("SELECT COUNT(*) FROM master_log").fetchone()[0],
                                   "would_remove": len(ids)}
    out["ids"]["master_log"] = ids
    for t, d in out["tables"].items():
        d["after"] = d["total"] - d["would_remove"]
    return out


def apply(con, db_file: Path, cfg: dict | None = None) -> dict:
    """ENFORCEMENT ONLY. Refuses unless enforce=true. Backup -> cold export -> delete."""
    cfg = cfg or config(force=True)
    if not enforcing(cfg):
        return {"ok": False, "refused": "enforce is false in data/config/governor.json (dry-run only)"}
    import shutil
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    bak = db_file.with_name(f"{db_file.name}.bak_governor_{stamp}")
    dst = sqlite3.connect(bak)
    con.backup(dst)
    dst.close()
    p = plan(con, cfg)
    cold = db_file.parent / "governor" / "cold"
    cold.mkdir(parents=True, exist_ok=True)
    removed = {}
    for t, ids in p["ids"].items():
        if not ids:
            continue
        cols = [r[1] for r in con.execute(f"PRAGMA table_info([{t}])")]
        with gzip.open(cold / f"{t}_{stamp}.jsonl.gz", "wt", encoding="utf-8") as fh:
            for i in range(0, len(ids), 500):
                part = ids[i:i + 500]
                for row in con.execute(f"SELECT * FROM [{t}] WHERE id IN ({','.join('?' * len(part))})", part):
                    fh.write(json.dumps(dict(zip(cols, row)), ensure_ascii=False) + "\n")
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            con.execute(f"DELETE FROM [{t}] WHERE id IN ({','.join('?' * len(part))})", part)
        removed[t] = len(ids)
    con.commit()
    _log({"table": "*", "action": "apply", "removed": removed, "backup": bak.name})
    return {"ok": True, "backup": str(bak), "cold": str(cold), "removed": removed,
            "note": "run VACUUM in a quiet window to return space to disk"}


# ---------------------------------------------------------------- replay (projected write-side effect)

def replay(con, cfg: dict | None = None, since: str = "") -> dict:
    """Re-run the write-side decisions over historical rows (read-only) -> projected skips."""
    cfg = cfg or config()
    res: dict[str, Any] = {"since": since}
    last: dict = {}
    n = 0
    acts: dict[str, int] = {}
    by_class: dict[str, int] = {}
    for _id, z, w, t, b in con.execute("SELECT id, zulu, whi, title, body FROM facts ORDER BY id"):
        key = (w, t)
        if z >= since:
            n += 1
            act = decide_fact(w, t, b, last.get(key), _epoch(z) or 0, cfg)
            if act:
                acts[act] = acts.get(act, 0) + 1
                by_class[w] = by_class.get(w, 0) + 1
                continue  # enforced: skipped row never becomes "last"
        last[key] = (z, b)
    res["facts"] = {"writes": n, "would_skip": sum(acts.values()), "by_action": acts,
                    "top_classes": dict(sorted(by_class.items(), key=lambda x: -x[1])[:8])}
    last, n, acts = {}, 0, {}
    for _id, z, s, b in con.execute("SELECT id, zulu, source, body FROM observations ORDER BY id"):
        if z >= since:
            n += 1
            act = decide_obs(s, b, last.get(s), _epoch(z) or 0, cfg)
            if act:
                acts[act] = acts.get(act, 0) + 1
                continue
        last[s] = (z, b)
    res["observations"] = {"writes": n, "would_skip": sum(acts.values()), "by_action": acts}
    last, n, k = {}, 0, 0
    win = int(cfg["packets"]["dedup_window_s"])
    for _id, z, d, kd, b in con.execute("SELECT id, zulu, dest, kind, body FROM packets ORDER BY id"):
        key = (d, kd)
        if z >= since:
            n += 1
            pl = last.get(key)
            if pl and pl[1] == b and (_epoch(z) or 0) - (_epoch(pl[0]) or 0) < win:
                k += 1
                continue
        last[key] = (z, b)
    res["packets"] = {"writes": n, "would_skip": k}
    seen, n, k = set(), 0, 0
    for _id, z, h, st in con.execute("SELECT id, zulu, hash, status FROM chunks ORDER BY id"):
        if z >= since:
            n += 1
            if h in seen:
                k += 1
                continue
        seen.add(h)
    res["chunks"] = {"writes": n, "would_skip": k, "note": "hash dedup vs earlier rows (any status, approx)"}
    return res


# ---------------------------------------------------------------- WHI (OG drain) ingest gate -- preview only

_ECHO = re.compile(r"(?im)^\s*(SCORE|TOPIC)\s*:|format exactly|follow-up research subjects|one per line|"
                   r"\(note for the new line|\(note: replace|replace \S+ with your|^\s*\(foo\)|\bfoo\b.*\bbar\b|"
                   r"\[link to public source\]")
_CITE = re.compile(r"(?i:https?://[^\s)]+|\(source:[^)]*\))|[Aa]ccording to [A-Z][\w.]+")
_FAKE_CITE = re.compile(r"(?i)example\.(com|org|net)|\[link|public source\]|yourdomain|placeholder|source\s*\d+\s*,\s*scored")


def clean_packet_text(text: str) -> str:
    lines = [ln for ln in (text or "").splitlines() if not re.match(r"(?i)^\s*(SCORE|TOPIC)\s*:", ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def whi_gate(pk: dict, cfg: dict, seen_hashes: set) -> tuple[bool, list[str], dict]:
    wc = cfg["whi"]
    reasons: list[str] = []
    body = pk.get("content") or ""
    clean = clean_packet_text(body)
    subj = (pk.get("subject") or "").strip()
    if (pk.get("status") or "") != "accepted":
        reasons.append(f"status={pk.get('status')}")
    if float(pk.get("score") or 0) < float(wc["min_score"]):
        reasons.append(f"score<{wc['min_score']}")
    if len(clean) < int(wc["min_chars"]):
        reasons.append("too_short")
    if len(clean) > int(wc["max_chars"]):
        reasons.append("too_long")
    if wc.get("reject_prompt_echo") and (_ECHO.search(clean) or _ECHO.search(subj)):
        reasons.append("prompt_echo")
    if not (8 <= len(subj) <= 160) or subj[:1] in "[(*" or subj.lower().startswith(("title:", "subject:")):
        reasons.append("bad_subject")
    found = [m.group(0) for m in _CITE.finditer(clean)]
    real = [c for c in found if not _FAKE_CITE.search(c)]
    if found and not real:
        reasons.append("fake_citation")
    su = pk.get("source_url") or ""
    cites = len(real) + (1 if su.startswith("http") and not _FAKE_CITE.search(su) else 0)
    if wc.get("require_citation") and cites < 1:
        reasons.append("no_citation")
    h = hashlib.sha256(re.sub(r"\s+", " ", clean.lower()).encode()).hexdigest()[:16]
    if h in seen_hashes:
        reasons.append("dup_hash")
    meta = {}
    try:
        meta = json.loads(pk.get("meta_json") or "{}")
    except Exception:
        pass
    row = {
        "whi": wc["land_whi"],
        "status": wc["land_status"],
        "hash": h,
        "source_cite": f"whi:{meta.get('node_id', 'tentacle-01')}:packet/{pk.get('id')}:{meta.get('job_id', '')}"
                       + (f":{pk['source_url']}" if pk.get("source_url") else ""),
        "text": "\n".join(f"{k}={v}" for k, v in (
            ("source_url", pk.get("source_url") or ""), ("accessed", pk.get("zulu")), ("llm", meta.get("model")),
            ("mask", "og-drain"), ("matrix_score", pk.get("score")), ("content_hash", h),
            ("whi", wc["land_whi"]), ("title", subj[:160])) if v not in (None, "")) + "\n\n" + clean[:7500],
    }
    return (not reasons), reasons, row


def whi_preview(node_db: str, nova_con=None, cfg: dict | None = None, limit_cycles: int = 1) -> dict:
    """Read-only: grade an OG NOVA_NODE.db snapshot through the WHI gate + per-cycle cap. Writes nothing."""
    cfg = cfg or config()
    src = sqlite3.connect(f"file:{node_db}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    seen = set()
    if nova_con is not None:
        seen |= {r[0] for r in nova_con.execute("SELECT hash FROM chunks")}
    cap = int(cfg["whi"]["max_packets_per_cycle"])
    ok_rows, rej = [], {}
    samples_rej = []
    total = 0
    for pk in src.execute("SELECT * FROM packets ORDER BY id"):
        total += 1
        good, reasons, row = whi_gate(dict(pk), cfg, seen)
        if good:
            seen.add(row["hash"])
            ok_rows.append((pk["id"], row))
        else:
            for r in reasons:
                rej[r] = rej.get(r, 0) + 1
            if len(samples_rej) < 6:
                samples_rej.append({"id": pk["id"], "subject": (pk["subject"] or "")[:70], "reasons": reasons})
    src.close()
    return {"node_db": node_db, "total": total, "pass_gate": len(ok_rows), "reject": total - len(ok_rows),
            "reject_reasons": dict(sorted(rej.items(), key=lambda x: -x[1])),
            "cap_per_cycle": cap, "first_cycle_would_land": min(cap, len(ok_rows)),
            "cycles_to_drain_passing": -(-len(ok_rows) // cap) if cap else None,
            "sample_pass": [{"packet_id": i, **{k: (v[:400] if isinstance(v, str) else v) for k, v in r.items()}}
                            for i, r in ok_rows[:3]],
            "sample_reject": samples_rej, "wrote": 0}


# ---------------------------------------------------------------- CLI

def _summary_log() -> dict:
    p = log_path()
    agg: dict[str, int] = {}
    if not p.is_file():
        return {"log": str(p), "lines": 0}
    n = 0
    with p.open(encoding="utf-8") as fh:
        for ln in fh:
            n += 1
            try:
                e = json.loads(ln)
                k = f"{e.get('table')}:{e.get('action')}:{e.get('whi') or e.get('source') or e.get('kind') or ''}"
                agg[k] = agg.get(k, 0) + 1
            except Exception:
                pass
    return {"log": str(p), "lines": n, "top": dict(sorted(agg.items(), key=lambda x: -x[1])[:20])}


def dry_run_report(db_file: Path, cfg: dict | None = None, write: bool = True) -> dict:
    """2.1: what ENFORCE mode would do, without doing it. Read-only DB; writes one JSON report
    under data/governor/ (never the DB). Enforce stays OFF unless governor.json says enforce:true."""
    cfg = cfg or config(force=True)
    con = sqlite3.connect(f"file:{Path(db_file).resolve().as_posix()}?mode=ro", uri=True)
    try:
        rep = {"generated": _zulu_now(), "enforce": cfg.get("enforce"), "enforcing": enforcing(cfg),
               "mode": "enforce" if enforcing(cfg) else "dry-run", "db_mb": round(os.path.getsize(db_file) / 1e6, 2)}
        try:
            rep["would_skip_writes"] = replay(con, cfg)
        except Exception as exc:
            rep["would_skip_writes"] = {"error": str(exc)[:160]}
        try:
            pl = plan(con, cfg)
            pl.pop("ids", None)
            rep["would_age_rows"] = pl
        except Exception as exc:
            rep["would_age_rows"] = {"error": str(exc)[:160]}
        rep["log"] = _summary_log()
    finally:
        con.close()
    if write:
        try:
            out = log_path().parent / "governor_dryrun_report.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
            rep["written"] = out.name
        except OSError:
            pass
    return rep


def main(argv: list[str] | None = None) -> int:
    import argparse
    from nova import db
    ap = argparse.ArgumentParser(prog="python -m nova.governor", description="NOVA data-sprawl governor (dry-run default)")
    ap.add_argument("cmd", choices=["status", "plan", "replay", "whi-preview", "log", "apply", "report"])
    ap.add_argument("--db", default=None, help="NOVA.db path (default: live kit DB, opened read-only)")
    ap.add_argument("--since", default="", help="replay: only rows with zulu >= this")
    ap.add_argument("--node-db", default=None, help="whi-preview: OG NOVA_NODE.db snapshot")
    a = ap.parse_args(argv)
    cfg = config(force=True)
    path = Path(a.db) if a.db else db.db_path()
    if a.cmd == "status":
        print(json.dumps({"config": str(config_path()), "config_exists": config_path().is_file(),
                          "enabled": cfg.get("enabled"), "enforce": cfg.get("enforce"), "enforcing": enforcing(cfg),
                          "db": str(path), "db_mb": round(os.path.getsize(path) / 1e6, 2),
                          "budget": cfg["budget"], "config_error": cfg.get("_config_error")}, indent=2))
        return 0
    if a.cmd == "log":
        print(json.dumps(_summary_log(), indent=2))
        return 0
    if a.cmd == "report":
        print(json.dumps(dry_run_report(path, cfg), indent=2))
        return 0
    if a.cmd == "apply":
        con = sqlite3.connect(path)
        try:
            print(json.dumps(apply(con, path, cfg), indent=2))
        finally:
            con.close()
        return 0
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        if a.cmd == "plan":
            p = plan(con, cfg)
            p.pop("ids", None)
            print(json.dumps(p, indent=2))
        elif a.cmd == "replay":
            print(json.dumps(replay(con, cfg, a.since), indent=2))
        elif a.cmd == "whi-preview":
            if not a.node_db:
                print("--node-db required", file=sys.stderr)
                return 2
            print(json.dumps(whi_preview(a.node_db, con, cfg), indent=2, ensure_ascii=True))
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
