"""Mailroom: packets, employees, report cards, hardware checksum."""

from __future__ import annotations

import hashlib
import json
import platform

from nova import db

VOICES = {
    "brief": "anna",
    "hearth": "anna",
    "tutor": "jane",
    "deleo": "michael",
    "sentinel": "javert",
    "chronicler": "charles",
    "reviewer": "george",
    "seer": "anna",
    "ear": "javert",
    "openclaw": "michael",
    "qwen": "george",
    "clerk": "anna",
}


def _ensure() -> None:
    con = db.connect()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS employees (
          id TEXT PRIMARY KEY,
          mask TEXT NOT NULL,
          model TEXT NOT NULL,
          voice TEXT,
          jobs_run INTEGER NOT NULL DEFAULT 0,
          accepted INTEGER NOT NULL DEFAULT 0,
          rejected INTEGER NOT NULL DEFAULT 0,
          agree INTEGER NOT NULL DEFAULT 0,
          dissent INTEGER NOT NULL DEFAULT 0,
          last_zulu TEXT,
          notes TEXT
        );
        CREATE TABLE IF NOT EXISTS packets (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          zulu TEXT NOT NULL,
          dest TEXT NOT NULL,
          mask TEXT,
          whi TEXT,
          kind TEXT,
          hash TEXT,
          cite TEXT,
          body TEXT,
          status TEXT NOT NULL DEFAULT 'queued'
        );
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          zulu TEXT NOT NULL,
          rank INTEGER NOT NULL,
          title TEXT NOT NULL,
          body TEXT,
          status TEXT NOT NULL DEFAULT 'open'
        );
        CREATE TABLE IF NOT EXISTS hw_inv (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          zulu TEXT NOT NULL,
          checksum TEXT NOT NULL,
          blob TEXT NOT NULL
        );
        """
    )
    con.commit()
    if not con.execute("SELECT id FROM employees LIMIT 1").fetchone():
        for mask, voice in VOICES.items():
            eid = f"{mask}@local"
            con.execute(
                "INSERT INTO employees(id, mask, model, voice) VALUES (?,?,?,?)",
                (eid, mask, "llama3-groq-tool-use:8b", voice),
            )
        con.commit()
    con.close()



def ensure_workforce() -> list[str]:
    """Upsert all VOICES employees into an existing palace (safe on live DB)."""
    _ensure()
    added: list[str] = []
    con = db.connect()
    defaults = {
        "seer": "moondream:latest",
        "qwen": "codellama:latest",
        "openclaw": "llama3-groq-tool-use:8b",
        "clerk": "qwen2:0.5b",
    }
    for mask, voice in VOICES.items():
        eid = f"{mask}@local"
        row = con.execute("SELECT id FROM employees WHERE id=?", (eid,)).fetchone()
        if row:
            continue
        model = defaults.get(mask, "llama3-groq-tool-use:8b")
        con.execute(
            "INSERT INTO employees(id, mask, model, voice) VALUES (?,?,?,?)",
            (eid, mask, model, voice),
        )
        added.append(eid)
    con.commit()
    con.close()
    return added


def staff() -> list[dict]:
    ensure_workforce()
    con = db.connect()
    rows = con.execute("SELECT * FROM employees ORDER BY id").fetchall()
    con.close()
    return [dict(r) for r in rows]


def bump(eid: str, field: str) -> None:
    _ensure()
    con = db.connect()
    if field not in {"jobs_run", "accepted", "rejected", "agree", "dissent"}:
        con.close()
        return
    con.execute(
        f"UPDATE employees SET {field}={field}+1, last_zulu=? WHERE id=?",
        (db.zulu(), eid),
    )
    con.commit()
    con.close()


def post_packet(**kw) -> int:
    _ensure()
    con = db.connect()
    # governor hook 2026-10-07: dry-run default = log only (returns None), never blocks
    try:
        from nova import governor as _gov
        _reuse = _gov.gate_packet(con, kw.get("dest") or "chronicler@local", kw.get("kind") or "ingest", (kw.get("body") or "")[:4000])
        if _reuse:
            con.close()
            return int(_reuse)
    except Exception:
        pass
    cur = con.execute(
        """INSERT INTO packets(zulu, dest, mask, whi, kind, hash, cite, body, status)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            db.zulu(),
            kw.get("dest") or "chronicler@local",
            kw.get("mask") or "chronicler",
            kw.get("whi") or "Tx",
            kw.get("kind") or "ingest",
            kw.get("hash") or "",
            kw.get("cite") or "",
            (kw.get("body") or "")[:4000],
            kw.get("status") or "queued",  # 2026-10-07 drain fix: callers may pass status="logged"
        ),
    )
    con.commit()
    pid = int(cur.lastrowid or 0)
    con.close()
    return pid


def report(rank: int, title: str, body: str) -> int:
    _ensure()
    con = db.connect()
    cur = con.execute(
        "INSERT INTO reports(zulu, rank, title, body, status) VALUES (?,?,?,?,?)",
        (db.zulu(), int(rank), title[:160], body[:2000], "open"),
    )
    con.commit()
    rid = int(cur.lastrowid or 0)
    con.close()
    return rid


def reports(open_only: bool = True) -> list[dict]:
    _ensure()
    con = db.connect()
    if open_only:
        rows = con.execute(
            "SELECT * FROM reports WHERE status='open' ORDER BY rank DESC, id DESC"
        ).fetchall()
    else:
        rows = con.execute("SELECT * FROM reports ORDER BY id DESC LIMIT 20").fetchall()
    con.close()
    return [dict(r) for r in rows]


def stamp_report(rid: int, status: str) -> None:
    con = db.connect()
    con.execute("UPDATE reports SET status=? WHERE id=?", (status, rid))
    con.commit()
    con.close()


def snapshot_hw() -> dict:
    blob = {
        "system": platform.system(),
        "node": platform.node(),
        "machine": platform.machine(),
    }
    try:
        import psutil

        blob["cpu"] = psutil.cpu_count(logical=True)
        blob["ram_gb"] = round(psutil.virtual_memory().total / 1024**3, 2)
        blob["cpu_pct"] = psutil.cpu_percent(interval=0.2)
    except Exception:
        pass
    cams = []
    try:
        import sys
        import cv2

        for idx in range(3):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(idx)
            if cap.isOpened():
                cams.append(
                    {
                        "index": idx,
                        "w": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
                        "h": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
                    }
                )
            cap.release()
    except Exception:
        pass
    blob["cams"] = cams
    try:
        from nova import thermal

        th = thermal.snapshot()
        blob["thermal"] = {
            "band": th.get("band"),
            "gpu_temp_c": (th.get("gpu") or {}).get("temp_c"),
            "gpu_util": (th.get("gpu") or {}).get("util_pct"),
            "vram_used_mib": (th.get("gpu") or {}).get("mem_used_mib"),
            "vram_free_mib": (th.get("gpu") or {}).get("mem_free_mib"),
            "cpu_temp_c": th.get("cpu_temp_c"),
            "llm_ok": th.get("llm_ok"),
        }
    except Exception as exc:
        blob["thermal"] = {"error": str(exc)}
    raw = json.dumps(blob, sort_keys=True)
    checksum = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return {"checksum": checksum, "blob": blob}


def hw_check() -> dict:
    _ensure()
    snap = snapshot_hw()
    con = db.connect()
    last = con.execute("SELECT checksum, blob FROM hw_inv ORDER BY id DESC LIMIT 1").fetchone()
    con.execute(
        "INSERT INTO hw_inv(zulu, checksum, blob) VALUES (?,?,?)",
        (db.zulu(), snap["checksum"], json.dumps(snap["blob"])),
    )
    con.commit()
    con.close()
    changed = not last or last["checksum"] != snap["checksum"]
    if changed:
        rid = report(
            2,
            "hardware map changed",
            json.dumps({"new": snap["checksum"], "old": last["checksum"] if last else None, "cams": snap["blob"].get("cams")}),
        )
        db.put_fact("Tx-HW", "checksum", snap["checksum"])
        return {"changed": True, "report": rid, "checksum": snap["checksum"]}
    db.put_fact("Ax-HW", "checksum", snap["checksum"])
    return {"changed": False, "checksum": snap["checksum"]}


_BIND = (
    ("sentinel", ("nova-sentinel", "qwen2:0.5b")),
    ("chronicler", ("nova-chronicler", "gemma2:2b")),
    ("deleo", ("nova-commander", "llama3-groq-tool-use")),
    ("reviewer", ("qwen3:8b", "qwen3.5", "codellama")),
    ("brief", ("llama3:8b", "llama3-groq")),
    ("tutor", ("llama3.2:3b", "phi3")),
    ("hearth", ("gemma2:2b", "llama3.2")),
    ("seer", ("moondream", "llava", "minicpm")),
    ("ear", ("nova-sentinel", "qwen2:0.5b")),
    ("openclaw", ("llama3-groq-tool-use", "llama3:8b")),
    ("qwen", ("codellama", "qwen3.5", "qwen3:8b")),
    ("clerk", ("qwen2:0.5b", "nova-sentinel", "gemma2:2b")),
)


def assign_from_roster(names: list[str]) -> dict:
    _ensure()
    bound = {}
    con = db.connect()
    for mask, hints in _BIND:
        pick = None
        for h in hints:
            for n in names:
                if h in n:
                    pick = n
                    break
            if pick:
                break
        if not pick and names:
            pick = names[0]
        if pick:
            con.execute(
                "UPDATE employees SET model=?, last_zulu=? WHERE mask=?",
                (pick, db.zulu(), mask),
            )
            bound[mask] = pick
    con.commit()
    con.close()
    return bound


def inbox(status: str = "queued", limit: int = 20) -> list[dict]:
    _ensure()
    con = db.connect()
    rows = con.execute(
        "SELECT * FROM packets WHERE status=? ORDER BY id LIMIT ?",
        (status, limit),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def deliver_inbox(limit: int = 3) -> list[dict]:
    """Load dest employee, read packet, write reply, mark delivered. Unload via keep_alive=0."""
    import json
    import urllib.request

    out = []
    for pkt in inbox("queued", limit):
        dest = pkt.get("dest") or "brief@local"
        crew = {e["id"]: e for e in staff()}
        emp = crew.get(dest) or {"mask": "brief", "model": "llama3-groq-tool-use:8b"}
        body = {
            "model": emp.get("model") or "llama3-groq-tool-use:8b",
            "messages": [
                {
                    "role": "system",
                    "content": f"You are {emp.get('mask')}. Read the mail. Reply in 3 lines. "
                    "If spoken, [speak {voice}] line [/speak].".replace(
                        "{voice}", emp.get("voice") or "anna"
                    ),
                },
                {"role": "user", "content": (pkt.get("body") or "")[:2000]},
            ],
            "stream": False,
            "keep_alive": 0,
        }
        reply = ""
        err = ""
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/chat",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode())
            reply = (data.get("message") or {}).get("content") or ""
        except Exception as exc:
            err = str(exc)
        con = db.connect()
        con.execute(
            "UPDATE packets SET status=?, body=? WHERE id=?",
            (
                "delivered" if not err else "fail",
                ((pkt.get("body") or "") + "\n---\n" + (reply or err))[:4000],
                pkt["id"],
            ),
        )
        con.commit()
        con.close()
        bump(dest, "jobs_run")
        out.append({"id": pkt["id"], "dest": dest, "err": err, "reply": reply[:160]})
    return out


def sync_voices_from_pocket() -> int:
    """Keep employee.voice aligned with pocket.SEATS (Pocket TTS only)."""
    from nova import pocket
    ensure_workforce()
    con = db.connect()
    n = 0
    for row in con.execute("SELECT id, mask, voice FROM employees").fetchall():
        mask = (row["mask"] or row["id"].split("@")[0]).lower()
        want = pocket.SEATS.get(mask) or pocket.DEFAULT_VOICE
        if (row["voice"] or "") != want:
            con.execute("UPDATE employees SET voice=? WHERE id=?", (want, row["id"]))
            n += 1
    con.commit()
    con.close()
    return n


def _config_dir():
    d = db.home() / "data" / "config"
    d.mkdir(parents=True, exist_ok=True)
    return d


def automate_queue_path():
    return _config_dir() / "automate_queue.json"


def get_automate_queue() -> bool:
    """Persisted Automate Queue flag (HIL bypass for auto-safe drains). Default False."""
    path = automate_queue_path()
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return bool(data.get("on"))
    except Exception:
        return False


def set_automate_queue(on: bool) -> dict:
    """Toggle Automate Queue; persists under data/config/automate_queue.json."""
    path = automate_queue_path()
    payload = {"on": bool(on), "zulu": db.zulu()}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        db.put_fact(
            "Ax-OPS",
            "automate-queue",
            f"on={int(bool(on))} path={path}",
            kind="homestead",
        )
    except Exception:
        pass
    return payload


def approve_all(*, reports: bool = True, board_queue: bool = True) -> dict:
    """HIL bulk Approve All — open report cards → approved; board queued → approved.

    Does NOT auto-send outbound mail/WhatsApp. Does NOT delete palace facts.
    """
    _ensure()
    out = {"reports": 0, "queue": 0, "zulu": db.zulu()}
    con = db.connect()
    if reports:
        cur = con.execute(
            "UPDATE reports SET status='approved' WHERE status='open'"
        )
        out["reports"] = int(cur.rowcount or 0)
    if board_queue:
        cur = con.execute(
            "UPDATE queue SET status='approved' WHERE status IN ('queued','pending')"
        )
        out["queue"] = int(cur.rowcount or 0)
    con.commit()
    con.close()
    try:
        db.put_fact(
            "Ax-OPS",
            "approve-all",
            json.dumps(out),
            kind="homestead",
        )
    except Exception:
        pass
    return out


def clear_standing_ingest(*, dry_run: bool = False, backup: bool = True) -> dict:
    """Standing clear like 2026-09-27: cancel/clear waiting work; never delete palace facts.

    - Backup NOVA.db (unless dry_run or backup=False)
    - docs_queue queued/running → cancelled
    - board URL queue queued/running http → cancelled
    - packets status=queued → cleared (rows kept)
    - data/queue/waiting/*.json → data/queue/cleared/
    """
    import shutil

    _ensure()
    home = db.home()
    zulu_raw = db.zulu()
    stamp = zulu_raw.replace(":", "").replace("-", "")
    out: dict = {
        "ok": True,
        "dry_run": bool(dry_run),
        "zulu": zulu_raw,
        "backup": None,
        "docs_queue": 0,
        "board_urls": 0,
        "packets": 0,
        "fs_waiting": 0,
        "fs_moved": [],
    }
    db_path = home / "data" / "NOVA.db"
    if backup and not dry_run and db_path.is_file():
        bak = home / "data" / f"NOVA.db.bak_clear_ingest_{stamp}"
        shutil.copy2(db_path, bak)
        out["backup"] = str(bak.name)

    con = db.connect()
    try:
        con.execute(
            """CREATE TABLE IF NOT EXISTS docs_queue (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              path TEXT, hash TEXT, status TEXT, zulu TEXT,
              note TEXT, last_err TEXT
            )"""
        )
        if dry_run:
            n = con.execute(
                "SELECT COUNT(*) AS c FROM docs_queue WHERE status IN ('queued','running')"
            ).fetchone()["c"]
            out["docs_queue"] = int(n or 0)
        else:
            cur = con.execute(
                "UPDATE docs_queue SET status='cancelled', note=? "
                "WHERE status IN ('queued','running')",
                (f"standing-clear {zulu_raw}",),
            )
            out["docs_queue"] = int(cur.rowcount or 0)
    except Exception as exc:
        out["docs_queue_err"] = str(exc)

    try:
        if dry_run:
            n = con.execute(
                "SELECT COUNT(*) AS c FROM queue WHERE status IN ('queued','running') "
                "AND description LIKE 'http%'"
            ).fetchone()["c"]
            out["board_urls"] = int(n or 0)
        else:
            cur = con.execute(
                "UPDATE queue SET status='cancelled' WHERE status IN ('queued','running') "
                "AND description LIKE 'http%'"
            )
            out["board_urls"] = int(cur.rowcount or 0)
    except Exception as exc:
        out["board_err"] = str(exc)

    try:
        if dry_run:
            n = con.execute(
                "SELECT COUNT(*) AS c FROM packets WHERE status='queued'"
            ).fetchone()["c"]
            out["packets"] = int(n or 0)
        else:
            cur = con.execute(
                "UPDATE packets SET status='cleared' WHERE status='queued'"
            )
            out["packets"] = int(cur.rowcount or 0)
    except Exception as exc:
        out["packets_err"] = str(exc)

    if not dry_run:
        con.commit()
    con.close()

    waiting = home / "data" / "queue" / "waiting"
    cleared = home / "data" / "queue" / "cleared"
    cleared.mkdir(parents=True, exist_ok=True)
    if waiting.is_dir():
        for fp in sorted(waiting.glob("*.json")):
            out["fs_waiting"] += 1
            if dry_run:
                out["fs_moved"].append(fp.name)
            else:
                dest = cleared / fp.name
                if dest.exists():
                    dest = cleared / f"{fp.stem}_{stamp}{fp.suffix}"
                shutil.move(str(fp), str(dest))
                out["fs_moved"].append(dest.name)

    if not dry_run:
        try:
            summary = {k: v for k, v in out.items() if k != "fs_moved"}
            summary["fs_n"] = len(out["fs_moved"])
            db.put_fact(
                "Ax-OPS",
                "standing-ingest-clear",
                json.dumps(summary),
                kind="homestead",
            )
        except Exception:
            pass
    return out
