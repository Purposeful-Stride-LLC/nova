"""Sound-bite queue. Workers comment after jobs. Parser + GUI drain it."""

from __future__ import annotations

import json

from nova import db, office, pocket

# job name prefix -> employee mask
ROUTE = {
    "holmes": "sentinel",
    "hw-check": "seer",
    "ollama-catalog": "deleo",
    "maintain": "chronicler",
    "whistle": "hearth",
    "cam": "seer",
    "web": "chronicler",
    "pdf": "reviewer",
    "codesum": "reviewer",
    "history": "sentinel",
    "brief-news": "brief",
}


def _ensure() -> None:
    con = db.connect()
    con.execute(
        """CREATE TABLE IF NOT EXISTS bites (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             zulu TEXT NOT NULL,
             worker TEXT NOT NULL,
             voice TEXT,
             job TEXT,
             line TEXT NOT NULL,
             path TEXT,
             status TEXT NOT NULL DEFAULT 'queued'
           )"""
    )
    try:
        con.execute("ALTER TABLE jobs ADD COLUMN worker TEXT")
    except Exception:
        pass
    con.commit()
    con.close()


def worker_for(job_name: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit.split("@")[0]
    seats = {
        "brief", "hearth", "tutor", "deleo", "sentinel",
        "chronicler", "reviewer", "seer", "ear",
    }
    if "@" in (job_name or ""):
        tail = job_name.rsplit("@", 1)[1].split(":")[0]
        if tail in seats:
            return tail
    head = (job_name or "").split(":")[0]
    return ROUTE.get(head, "brief")


def enqueue(job: str, line: str, worker: str | None = None) -> int:
    _ensure()
    mask = worker_for(job, worker)
    voice = pocket.resolve_voice(mask)
    con = db.connect()
    cur = con.execute(
        "INSERT INTO bites(zulu, worker, voice, job, line, status) VALUES (?,?,?,?,?,?)",
        (db.zulu(), f"{mask}@local", voice, job, line[:180], "queued"),
    )
    con.commit()
    bid = int(cur.lastrowid or 0)
    con.close()
    office.bump(f"{mask}@local", "jobs_run")
    return bid


def queued(limit: int = 20) -> list[dict]:
    _ensure()
    con = db.connect()
    rows = con.execute(
        "SELECT * FROM bites ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def play_next() -> dict:
    _ensure()
    con = db.connect()
    row = con.execute(
        "SELECT * FROM bites WHERE status='queued' ORDER BY id LIMIT 1"
    ).fetchone()
    if not row:
        con.close()
        return {"ok": False, "error": "empty queue"}
    rec = dict(row)
    con.close()
    res = pocket.speak(rec["line"], rec.get("voice") or "anna")
    con = db.connect()
    con.execute(
        "UPDATE bites SET status=?, path=? WHERE id=?",
        ("played" if res.get("ok") else "fail", res.get("path") or "", rec["id"]),
    )
    con.commit()
    con.close()
    return {"ok": True, "bite": rec, "tts": res}


def after_job(job: str, note: str, err: str, worker: str | None = None) -> int:
    mask = worker_for(job, worker)
    if err:
        line = f"{mask} failed {job.split(':')[0]}."
    else:
        line = f"{mask} finished {job.split(':')[0]}."
        if note:
            line = f"{mask}: {note[:60]}"
    return enqueue(job, line, mask)
