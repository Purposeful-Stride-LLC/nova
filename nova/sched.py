"""Scheduler v2 (fieldkit 2.1). TUI/GUI/chat PROPOSE; the daemon ticks and executes.

New in 2.1:
- detailed job table (id, name, cadence, priority, GPU class, last run, next run, last error, enabled)
- GPU-exclusivity classes (gpulock): at most one heavy/vision model job at a time
- exponential backoff for failing jobs (base * 2^(fails-1), capped)
- command inbox (cmdinbox): approved commands only, executed at the start of each tick
- task-stimulus job: open reports / queued items / stale checks -> NOW lines + HIL proposals
State lives in <NOVA_HOME>/data/run/sched_state.json (no DB schema change).
Overrides: <NOVA_HOME>/data/config/scheduler.json {"jobs": {name: {priority, gpu}}, "backoff": {...}}.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from nova import db

_LAST: dict[int, float] = {}

# priority: higher runs first within a tick. gpu: none | light | vision | heavy
JOB_META: dict[str, dict] = {
    "thermal-check": {"priority": 90, "gpu": "none"},
    "task-stimulus": {"priority": 80, "gpu": "none"},
    "holmes": {"priority": 70, "gpu": "none"},
    "cam": {"priority": 60, "gpu": "none"},
    "camsee": {"priority": 55, "gpu": "vision"},
    "whistle": {"priority": 20, "gpu": "none"},
    "ingest-drain": {"priority": 40, "gpu": "light"},
    "docs-ingest": {"priority": 40, "gpu": "light"},
    "docs-scout": {"priority": 35, "gpu": "none"},
    "homestead-cycle": {"priority": 30, "gpu": "none"},
    "nova-diary": {"priority": 25, "gpu": "light"},
    "maintain": {"priority": 10, "gpu": "heavy"},
    "codesum": {"priority": 15, "gpu": "heavy"},
    "qwen": {"priority": 15, "gpu": "heavy"},
    "council-series": {"priority": 10, "gpu": "none"},
    "ollama-catalog": {"priority": 30, "gpu": "none"},
    "hw-check": {"priority": 50, "gpu": "none"},
}
BACKOFF = {"base_s": 60, "max_s": 6 * 3600}


def _cfg() -> dict:
    try:
        p = db.home() / "data" / "config" / "scheduler.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except Exception:
        return {}


def meta(name: str) -> dict:
    k = _key(name)
    base = k.split(":", 1)[0] if ":" in k and k not in JOB_META else k
    m = dict(JOB_META.get(k) or JOB_META.get(base) or {"priority": 30, "gpu": "none"})
    m.update((_cfg().get("jobs") or {}).get(k) or {})
    return m


def _state_path():
    d = db.home() / "data" / "run"
    d.mkdir(parents=True, exist_ok=True)
    return d / "sched_state.json"


def load_state() -> dict:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(st: dict) -> None:
    p = _state_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def _backoff_s(fails: int) -> int:
    b = {**BACKOFF, **(_cfg().get("backoff") or {})}
    if fails <= 0:
        return 0
    return int(min(b["max_s"], b["base_s"] * (2 ** (fails - 1))))


def request_run_now(jid: int) -> None:
    st = load_state()
    st.setdefault(str(jid), {})["run_now"] = True
    save_state(st)


def next_run(row: dict, st: dict, now: float) -> float:
    js = st.get(str(row["id"])) or {}
    if js.get("run_now"):
        return now
    last = float(js.get("last_run") or _LAST.get(row["id"], 0) or 0)
    if not last and row.get("last_zulu"):  # fall back to the DB stamp (daemon restart, GUI view)
        from nova.ctime import parse_zulu
        t = parse_zulu(row.get("last_zulu"))
        last = t.timestamp() if t else 0
    every = max(15, int(row.get("every_s") or 60))
    return max(last + every, float(js.get("backoff_until") or 0))


def due(now: float | None = None) -> list[dict]:
    now = now or time.time()
    st = load_state()
    out = []
    for row in db.jobs():
        if not row.get("enabled") and not (st.get(str(row["id"])) or {}).get("run_now"):
            continue
        if now >= next_run(row, st, now):
            out.append(row)
    out.sort(key=lambda r: -int(meta(r["name"]).get("priority") or 0))
    return out


def mark(jid: int) -> None:
    _LAST[jid] = time.time()


def record(jid: int, err: str, now: float | None = None) -> dict:
    now = now or time.time()
    st = load_state()
    js = st.setdefault(str(jid), {})
    js["last_run"] = now
    js["run_now"] = False
    if err:
        js["fails"] = int(js.get("fails") or 0) + 1
        js["last_err"] = err[:200]
        js["backoff_until"] = now + _backoff_s(js["fails"])
    else:
        js["fails"] = 0
        js["backoff_until"] = 0
    save_state(st)
    return js


def _fmt(ts) -> str:
    if not ts:
        return "-"
    from nova.ctime import fmt
    return fmt(datetime.fromtimestamp(float(ts), tz=timezone.utc))


def _fmt_z(z) -> str:
    from nova.ctime import fmt, parse_zulu
    t = parse_zulu(z) if z else None
    return fmt(t) if t else "-"


def job_table(now: float | None = None, rows_in: list[dict] | None = None) -> list[dict]:
    """Detailed, read-only job table for TUI/GUI/docs. GUI passes rows read on a mode=ro connection."""
    now = now or time.time()
    st = load_state()
    rows = []
    for r in (rows_in if rows_in is not None else db.jobs()):
        js = st.get(str(r["id"])) or {}
        m = meta(r["name"])
        nr = next_run(r, st, now) if r.get("enabled") else None
        rows.append({
            "id": r["id"], "name": r["name"], "cadence_s": r.get("every_s"), "priority": m.get("priority"),
            "gpu": m.get("gpu"), "enabled": int(r.get("enabled") or 0),
            "last_run": _fmt(js.get("last_run")) if js.get("last_run") else _fmt_z(r.get("last_zulu")),
            "next_run": ("-" if not r.get("enabled") else ("due now" if nr is not None and nr <= now else _fmt(nr))),
            "last_error": js.get("last_err") or r.get("last_err") or "",
            "fails": int(js.get("fails") or 0),
            "backoff_until": _fmt(js.get("backoff_until")) if js.get("backoff_until") else "-",
        })
    return rows


def table_text(rows: list[dict] | None = None) -> str:
    rows = rows if rows is not None else job_table()
    hdr = f"{'id':>3} {'name':22} {'every':>6} {'pri':>3} {'gpu':6} {'en':2} {'last run':18} {'next run':18} {'fails':>5} last error"
    lines = [hdr]
    for r in rows:
        lines.append(f"{r['id']:>3} {r['name'][:22]:22} {r['cadence_s']:>6} {r['priority']:>3} {r['gpu']:6} {r['enabled']:>2} "
                     f"{str(r['last_run'])[:18]:18} {str(r['next_run'])[:18]:18} {r['fails']:>5} {r['last_error'][:40]}")
    return "\n".join(lines)


def _key(name: str) -> str:
    return (name or "").split("@")[0]



def _codesum_model() -> str:
    from nova import ollama_talk

    tags = ollama_talk.tags()
    for hint in ("codellama", "qwen3.5:9b", "qwen3:8b", "llama3-groq-tool-use:8b"):
        for n in tags:
            if hint in n:
                return n
    return "llama3-groq-tool-use:8b"

def run_named(name: str) -> dict:
    t0 = db.zulu()
    t_wall = time.perf_counter()
    err = ""
    note = ""
    key = _key(name)
    try:
        if key == "holmes":
            from nova import holmes

            sw = holmes.sweep()
            note = f"probes={len(sw.get('probes') or [])} watson={1 if (sw.get('watson') or {}).get('ok') else 0}"
        elif key == "maintain":
            note = maintain()
        elif key == "ollama-catalog":
            from nova import router

            names = router.catalog()
            note = ",".join(names[:8])
        elif key.startswith("codesum:"):
            from nova.hands import codesum

            note = str(codesum.run(key.split(":", 1)[1], _codesum_model()))[:200]
        elif key == "history":
            from nova.hands import history

            note = str(history.ingest())[:200]
        elif key.startswith("pdf:"):
            from nova.hands import pdf

            note = str(pdf.ingest(key.split(":", 1)[1]))[:200]
        elif key.startswith("web:"):
            from nova.hands import web

            note = str(web.fetch(key.split(":", 1)[1]))[:200]
        elif key == "hw-check":
            from nova import office

            note = str(office.hw_check())
        elif key.startswith("cam:"):
            from nova import senses

            idx = int(key.split(":", 1)[1] or 0)
            still = senses.save_still(idx)
            note = str(still)[:200]
            # Optional VLM only when steward job is camsee:N (not every cam tick)
        elif key.startswith("camsee:"):
            from nova import senses

            idx = int(key.split(":", 1)[1] or 0)
            still = senses.save_still(idx)
            extra = {}
            if still.get("ok") and still.get("path"):
                tags = senses.vision_tags()
                if tags:
                    model = "moondream" if any("moondream" in t for t in tags) else tags[0]
                    extra = senses.describe(still["path"], model)
                    # elevate on strong motion cue in features
                    feat = still.get("features") or {}
                    if int(feat.get("n_contours") or 0) > 40:
                        from nova import office

                        office.report(2, f"camsee motion-ish cam:{idx}", str(extra)[:500])
            note = str({"still": still.get("ok"), "vlm": extra})[:200]
        elif key == "whistle":
            note = whistle()
        elif key == "task-stimulus":
            from nova import taskstim
            r = taskstim.run()
            note = f"now={len(r.get('now') or [])} proposed={r.get('proposed')} dup={r.get('duplicates')}"
        elif key == "docs-scout":
            from nova import docs_ingest
            note = str(docs_ingest.scout())[:200]
        elif key == "docs-ingest":
            from nova import docs_ingest, thermal
            g = thermal.gate("llm")
            if not g.get("allow"):
                note = f"thermal_skip {g.get('reason')} band={(g.get('snap') or {}).get('band')}"
            else:
                band = (g.get("snap") or {}).get("band")
                lim = 2 if band == "cool" else 1
                d = docs_ingest.ingest_due(limit=lim, model="qwen2:0.5b", mask="chronicler")
                note = f"n={d.get('n')} ok={d.get('ok')} band={band}"
        elif key == "ingest-drain":
            from nova import crawl, thermal
            g = thermal.gate("llm")
            if not g.get("allow"):
                note = f"thermal_skip {g.get('reason')}"
            else:
                band = (g.get("snap") or {}).get("band")
                lim = 8 if band == "cool" else 4
                d = crawl.drain_temps_through_pipe(limit=lim, model="qwen2:0.5b", mask="chronicler", min_score=28)
                note = "drain_n=" + str((d or {}).get("n")) + f" band={band}"
        elif key == "nova-diary":
            from nova import novadiary
            d = novadiary.write_entry(theme="homestead evening")
            note = f"ok={d.get('ok')} chars={d.get('chars')} err={d.get('error')}"
        elif key == "thermal-check":
            from nova import thermal
            snap = thermal.snapshot()
            thermal.record_fact(snap)
            note = f"band={snap.get('band')} temp={(snap.get('gpu') or {}).get('temp_c')} llm_ok={snap.get('llm_ok')}"

        elif key == "homestead-cycle":
            from nova import homestead
            cyc = homestead.cycle()
            th = cyc.get("thermal") or {}
            note = f"needs={len(cyc.get('needs') or [])} band={th.get('band')} temp={th.get('gpu_temp')} root={(cyc.get('scan') or {}).get('root')}"
        elif key == "mail":
            from nova import office

            note = str(office.deliver_inbox(3))[:200]
        elif key == "ingest":
            from nova import board

            note = str(board.drain_one())[:200]
        elif key == "claw-ping":
            from nova import claw

            note = str(claw.status())[:200]
        elif key == "claw-run":
            # Deliver one queued openclaw@local task via real OpenClaw CLI
            from nova import leash, office

            queued = [p for p in office.inbox("queued", 20) if (p.get("dest") or "").startswith("openclaw") and p.get("kind") == "task"]
            if not queued:
                note = "no openclaw task queued"
            else:
                pkt = queued[0]
                note = str(leash.openclaw_run(pkt.get("body") or "", packet_id=pkt["id"]))[:200]
        elif key == "claw-grok":
            import os
            from nova import leash as _leash

            q = (os.environ.get("NOVA_GROK_QUERY") or "").strip()
            live = (os.environ.get("NOVA_GROK_LIVE") or "").strip().lower() in {"1", "true", "yes"}
            if not q:
                note = "claw-grok needs NOVA_GROK_QUERY; dry unless NOVA_GROK_LIVE=1"
                return {"ok": False, "job": key, "note": note}
            res = _leash.grok_query(q, dry_run=not live, deliver=live)
            note = str(res)[:400]
            return {"ok": bool(res.get("ok")), "job": key, "note": note}
        elif key == "claw-gemini":
            import os
            from nova import leash as _leash

            q = (os.environ.get("NOVA_GEMINI_QUERY") or "").strip()
            live = (os.environ.get("NOVA_GEMINI_LIVE") or "").strip().lower() in {"1", "true", "yes"}
            if not q:
                note = "claw-gemini needs NOVA_GEMINI_QUERY; dry unless NOVA_GEMINI_LIVE=1"
                return {"ok": False, "job": key, "note": note}
            res = _leash.gemini_query(q, dry_run=not live, deliver=live, steward_cdp=True)
            note = str(res)[:400]
            return {"ok": bool(res.get("ok")), "job": key, "note": note}
        elif key == "openclaw-status":
            from nova import leash

            note = str(leash.openclaw_status())[:200]
        elif key.startswith("crawl:"):
            from nova import crawl as crawlmod

            url = key.split(":", 1)[1].strip()
            note = str(crawlmod.crawl(url, max_pages=3, max_depth=2))[:200]
        elif key.startswith("qwen:"):
            from nova.hands import qwen as qwen_hand

            prompt = key.split(":", 1)[1].strip() or "Say pong"
            # If looks like a path, ask qwen to summarize that path
            from pathlib import Path as P
            if prompt and (P(prompt).exists() or chr(92) in prompt or "/" in prompt):
                prompt = f"List or summarize paths only, no writes: {prompt}"
            note = str(qwen_hand.run_prompt(prompt, timeout=180))[:200]
        elif key == "qwen-status":
            from nova import leash

            note = str(leash.qwen_status())[:200]
        elif key == "workforce":
            from nova import office

            note = str(office.ensure_workforce())[:200]
        elif key == "council-series":
            # Agenda-only by default; no GPU unless STEWARD_RUN=1 (stub still skips chamber)
            from nova import council_series

            note = str(council_series.run_stub())[:200]
        elif key in {"ingest-clear-daily", "clear-standing-ingest"}:
            from nova import office

            # Safe standing clear; never deletes palace facts. Backup on live run.
            res = office.clear_standing_ingest(dry_run=False, backup=True)
            # When Automate Queue is ON, also bulk-approve open HIL report cards.
            approved = None
            if office.get_automate_queue():
                approved = office.approve_all(reports=True, board_queue=False)
            note = (
                f"docs={res.get('docs_queue')} urls={res.get('board_urls')} "
                f"pkts={res.get('packets')} fs={res.get('fs_waiting')} "
                f"bak={res.get('backup')} auto={approved}"
            )[:200]
        else:
            err = f"unknown job {key}. /tools"
    except Exception as exc:
        err = str(exc)
        try:
            from nova import breaklog

            breaklog.record(key or name, err, severity="error", cite=f"job:{name}")
        except Exception:
            pass
    ms = int((time.perf_counter() - t_wall) * 1000)
    t1 = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.log(name, t0, t1, ms, err, note)
    return {"job": name, "ms": ms, "err": err, "note": note}


def maintain() -> str:
    con = db.connect()
    try:
        from nova import whi
        whi.ensure_indexes(con)
    except Exception:
        pass
    rows = con.execute("SELECT id, title, n_turns FROM conversations").fetchall()
    n = 0
    for row in rows:
        turns = con.execute(
            "SELECT body FROM turns WHERE conv=? ORDER BY id DESC LIMIT 20",
            (row["id"],),
        ).fetchall()
        blob = " ".join(t["body"] for t in turns)
        from nova.matrix import analyze

        m = analyze(blob)
        top = ", ".join(w for w, _ in (m.get("top") or [])[:6])
        title = top[:80] or row["title"]
        db.conv_meta(row["id"], title, top[:80], top)
        n += 1
    con.close()
    # Cut 1: auto-drain crawl temps through ingest_pipe (matrix + LLM + provenance)
    drained = 0
    try:
        from nova import crawl
        d = crawl.drain_temps_through_pipe(limit=8, model="qwen3:8b", mask="chronicler", min_score=28)
        drained = int((d or {}).get("n") or 0)
    except Exception as exc:
        return f"convs={n} drain_err={exc}"
    # 2.1: no deletes from the daemon. Rotation is CONFIG + dry-run report (nova.disk).
    try:
        from nova import disk
        rep = disk.dry_run_report(write=True)
        purged = f"dryrun_would_free_mb={rep.get('total_mb')}"
    except Exception as exc:
        purged = f"dryrun_err={exc}"
    return f"convs={n} drain={drained} tts_gc={purged}"


def whistle() -> str:
    import random
    from datetime import datetime, timezone

    from nova import office, pocket, db

    office._ensure()
    crew = office.staff()
    emp = random.choice(crew) if crew else {"id": "hearth@local", "voice": "anna", "mask": "hearth"}
    # Cut 4: WHI lag L0 — if newest fact older than 5 minutes, alert with sentinel voice
    lag_line = None
    try:
        con = db.connect()
        row = con.execute("SELECT zulu FROM facts ORDER BY id DESC LIMIT 1").fetchone()
        con.close()
        if row and row["zulu"]:
            z = str(row["zulu"]).replace("Z", "+00:00")
            try:
                ts = datetime.fromisoformat(z)
            except Exception:
                ts = None
            if ts is not None:
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                if age > 300:
                    lag_line = f"Palace WHI lag {int(age)} seconds. Steward, check ingest."
                    emp = {"id": "sentinel@local", "voice": "javert", "mask": "sentinel"}
    except Exception:
        pass
    line = lag_line or random.choice(
        [
            "Still here. Offline. Private.",
            "Queue is law.",
            "Have you eaten, biologic.",
            "Palace holds.",
        ]
    )
    voice = pocket.resolve_voice(emp.get("voice") or emp.get("mask") or "anna")
    try:
        r = pocket.speak(line, voice)
        play = (r or {}).get("play") or {}
        play_note = f" play={play.get('ok')}" if play else ""
    except Exception as exc:
        return f"tts {exc}"
    office.bump(emp.get("id") or "hearth@local", "jobs_run")
    return f"{emp.get('id')} {line}{play_note}"


def tick() -> list[dict]:
    """One daemon tick: approved commands first, then due jobs by priority; one heavy job max."""
    ran = []
    try:
        from nova import cmdinbox
        for rec in cmdinbox.execute_approved():
            ran.append({"job": "cmd:" + rec["verb"], "ms": 0, "err": "" if (rec.get("result") or {}).get("ok") else "failed",
                        "note": f"id={rec['id']}"})
    except Exception as exc:
        ran.append({"job": "cmdinbox", "ms": 0, "err": str(exc)[:200], "note": ""})
    from nova import gpulock
    heavy_used = False
    for row in due():
        m = meta(row["name"])
        cls = m.get("gpu") or "none"
        lock = None
        if cls in gpulock.EXCLUSIVE:
            if heavy_used:
                continue  # next tick; one exclusive GPU job per tick
            lock = gpulock.acquire("daemon:" + row["name"], cls, ttl_s=1800)
            if not lock.get("ok"):
                ran.append({"job": row["name"], "ms": 0, "err": "", "note": f"deferred gpu_busy by {lock.get('held_by')}"})
                continue
            heavy_used = True
        mark(row["id"])
        try:
            res = run_named(row["name"])
        finally:
            if lock and lock.get("lock"):
                gpulock.release("daemon:" + row["name"])
        db.job_touch(row["id"], res.get("err") or "", res.get("ms") or 0)
        js = record(row["id"], res.get("err") or "")
        if js.get("fails"):
            res["backoff_s"] = _backoff_s(js["fails"])
        try:
            from nova import bites

            bites.after_job(
                row["name"],
                res.get("note") or "",
                res.get("err") or "",
                row.get("worker"),
            )
        except Exception:
            pass
        ran.append(res)
    return ran


def main(argv: list[str] | None = None) -> int:
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] == "table":
        print(table_text())
        return 0
    if a[0] == "json":
        print(json.dumps(job_table(), indent=1))
        return 0
    print("usage: python -m nova.sched [table|json]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
