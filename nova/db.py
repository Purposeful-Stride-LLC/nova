"""SQLite palace. Creates schema if the file is missing."""

from __future__ import annotations

import re

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zulu TEXT NOT NULL,
  source TEXT NOT NULL,
  ok INTEGER NOT NULL,
  body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zulu TEXT NOT NULL,
  description TEXT NOT NULL,
  risk TEXT NOT NULL DEFAULT 'low',
  status TEXT NOT NULL DEFAULT 'queued'
);
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zulu TEXT NOT NULL,
  whi TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zulu TEXT NOT NULL,
  channel TEXT NOT NULL,
  summary TEXT NOT NULL
);
"""


def zulu() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def home() -> Path:
    env = os.environ.get("NOVA_HOME")
    if env:
        p = Path(env)
    else:
        p = Path.home() / "NOVA"
        if not (p / "nova").exists() and Path.cwd().joinpath("nova").exists():
            p = Path.cwd()
    (p / "data" / "artifacts").mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    d = home() / "data"
    for name in ("NOVA.db", "nova_agent.db"):
        cand = d / name
        if cand.exists():
            return cand
    return d / "NOVA.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    fresh = not path.exists()
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    try:
        from nova import whi as _whi
        con.executescript(
            """CREATE TABLE IF NOT EXISTS chunks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              zulu TEXT NOT NULL,
              whi TEXT NOT NULL,
              source_cite TEXT NOT NULL,
              text TEXT NOT NULL,
              hash TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'temp'
            );"""
        )
        _whi.ensure_indexes(con)
    except Exception:
        pass
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL, every_s INTEGER NOT NULL,
          enabled INTEGER NOT NULL DEFAULT 1,
          last_zulu TEXT, last_err TEXT, last_ms INTEGER
        );
        CREATE TABLE IF NOT EXISTS conversations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          opened TEXT NOT NULL, title TEXT NOT NULL,
          subject TEXT, words TEXT, n_turns INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS turns (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conv INTEGER NOT NULL, zulu TEXT NOT NULL, role TEXT NOT NULL, body TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS master_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          zulu TEXT NOT NULL, job TEXT NOT NULL, t0 TEXT, t1 TEXT,
          ms INTEGER, err TEXT, note TEXT
        );
        """
    )
    if fresh:
        con.execute(
            "INSERT INTO ledger(zulu, channel, summary) VALUES (?,?,?)",
            (zulu(), "boot", f"Schema created at {path}"),
        )
        con.execute(
            "INSERT INTO queue(zulu, description, risk, status) VALUES (?,?,?,?)",
            (zulu(), "Keep Ollama on 127.0.0.1:11434", "medium", "queued"),
        )
        if not con.execute("SELECT id FROM jobs LIMIT 1").fetchone():
            con.execute("INSERT INTO jobs(name, every_s, enabled) VALUES ('holmes', 300, 1)")
            con.execute("INSERT INTO jobs(name, every_s, enabled) VALUES ('maintain', 86400, 1)")
        con.commit()
    if not con.execute("SELECT id FROM jobs LIMIT 1").fetchone():
        con.execute("INSERT INTO jobs(name, every_s, enabled) VALUES ('holmes', 300, 1)")
        con.execute("INSERT INTO jobs(name, every_s, enabled) VALUES ('maintain', 86400, 1)")
        con.execute("INSERT INTO jobs(name, every_s, enabled) VALUES ('hw-check', 600, 1)")
        con.execute("INSERT INTO jobs(name, every_s, enabled) VALUES ('ollama-catalog', 600, 1)")
        con.execute("INSERT INTO jobs(name, every_s, enabled) VALUES ('whistle', 900, 1)")
        con.commit()
    return con


def insert_obs(source: str, ok: bool, body: str) -> None:
    try:
        con = connect()
        con.execute(
            "INSERT INTO observations(zulu, source, ok, body) VALUES (?,?,?,?)",
            (zulu(), source, int(ok), body[:4000]),
        )
        con.commit()
        con.close()
    except sqlite3.Error:
        return


def latest_obs(n: int = 12) -> list[dict]:
    con = connect()
    rows = con.execute(
        "SELECT zulu, source, ok, body FROM observations ORDER BY id DESC LIMIT ?",
        (n,),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def queue_rows(status: str | None = None) -> list[dict]:
    con = connect()
    if status:
        rows = con.execute(
            "SELECT id, zulu, description, risk, status FROM queue WHERE status=? ORDER BY id",
            (status,),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT id, zulu, description, risk, status FROM queue ORDER BY id"
        ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def set_queue(qid: int, status: str) -> None:
    con = connect()
    con.execute("UPDATE queue SET status=? WHERE id=?", (status, qid))
    con.execute(
        "INSERT INTO ledger(zulu, channel, summary) VALUES (?,?,?)",
        (zulu(), "queue", f"{qid} -> {status}"),
    )
    con.commit()
    con.close()


def hunt(q: str) -> list[dict]:
    """Word hunt; if q looks like WHI (Ax-|Tx-|0x-), use indexed whi filter first."""
    ensure_whi_indexes()
    q = (q or "").strip()
    con = connect()
    hits: list[dict] = []
    # WHI-keyed path
    if q.startswith(("Ax-", "Tx-", "0x-")) or q.upper().startswith(("AX-", "TX-", "0X-")):
        key = q if q[:3] in ("Ax-", "Tx-", "0x-") else (q[:2].upper().replace("AX", "Ax").replace("TX", "Tx").replace("0X", "0x") + q[2:])
        # normalize prefix case
        for pref in ("Ax-", "Tx-", "0x-"):
            if q.lower().startswith(pref.lower()):
                key = pref + q[len(pref):]
                break
        rows = con.execute(
            "SELECT zulu, whi, title, body FROM facts WHERE whi = ? OR whi LIKE ? ORDER BY id DESC LIMIT 40",
            (key, key + "%"),
        ).fetchall()
        hits = [{**dict(r), "score": 100} for r in rows]
    if not hits:
        tokens = [t for t in q.lower().split() if len(t) > 2]
        rows = con.execute(
            "SELECT zulu, whi, title, body FROM facts ORDER BY id DESC LIMIT 80"
        ).fetchall()
        for r in rows:
            blob = f"{r['title']} {r['body']}".lower()
            score = sum(1 for tok in tokens if tok in blob)
            if score:
                hits.append({**dict(r), "score": score})
        hits.sort(key=lambda x: -x["score"])
    if not hits and q:
        con.execute(
            "INSERT INTO facts(zulu, whi, title, body) VALUES (?,?,?,?)",
            (zulu(), "Tx-HUNT-MISS", q[:80], "No palace hit. LLM stays idle."),
        )
        con.commit()
    con.close()
    return hits[:8]




def ensure_whi_indexes() -> None:
    """Create WHI indexes on facts/chunks (idempotent)."""
    from nova import whi

    con = connect()
    # chunks table may already exist via chamber/crawl
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS chunks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          zulu TEXT NOT NULL,
          whi TEXT NOT NULL,
          source_cite TEXT NOT NULL,
          text TEXT NOT NULL,
          hash TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'temp'
        );
        """
    )
    whi.ensure_indexes(con)
    con.commit()
    con.close()


def put_fact(whi: str, title: str, body: str, **meta) -> None:
    """Format contract: wing whi Ax-|Tx-|0x-; non-empty title; body preferred.

    Pass whi='auto' or kind=... to build WHI from subject matter (nova.whi.classify).
    """
    from nova import whi as whi_mod

    w = (whi or "").strip()
    if w.lower() in {"", "auto"} or meta.get("kind"):
        w = whi_mod.classify(
            str(body or ""),
            title=str(title or ""),
            url=str(meta.get("source_url") or meta.get("url") or ""),
            kind=str(meta.get("kind") or ""),
            default="Tx-TEMP" if w.lower() in {"", "auto"} else w,
        )
    if not (w.startswith("Ax-") or w.startswith("Tx-") or w.startswith("0x-")):
        raise ValueError(f"whi must be Ax-|Tx-|0x- wing, got {w!r}")
    title = re.sub(r"\s+", " ", (title or "").strip())
    if not title:
        title = meta.get("fallback_title") or w
    body = body if body is not None else ""
    if not str(body).strip():
        reason = meta.get("reason") or meta.get("label") or "empty-body"
        body = f"reason={reason}"
        if meta.get("source_url"):
            body += f"\nurl={meta['source_url']}"
    con = connect()
    con.execute(
        "INSERT INTO facts(zulu, whi, title, body) VALUES (?,?,?,?)",
        (zulu(), w, title[:160], str(body)[:8000]),
    )
    con.commit()
    con.close()


def log(job: str, t0: str, t1: str, ms: int, err: str = "", note: str = "") -> None:
    try:
        con = connect()
        con.execute(
            "INSERT INTO master_log(zulu, job, t0, t1, ms, err, note) VALUES (?,?,?,?,?,?,?)",
            (zulu(), job, t0, t1, ms, err or "", (note or "")[:500]),
        )
        con.commit()
        con.close()
        p = home() / "data" / "master.log"
        with p.open("a", encoding="utf-8") as fh:
            fh.write(f"{t1} job={job} ms={ms} err={err} {note}\n")
    except sqlite3.Error:
        return


def jobs() -> list[dict]:
    con = connect()
    rows = con.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    con.close()
    return [dict(r) for r in rows]


def job_set(jid: int, **fields) -> None:
    con = connect()
    if "enabled" in fields:
        con.execute("UPDATE jobs SET enabled=? WHERE id=?", (int(fields["enabled"]), jid))
    if "every_s" in fields:
        con.execute("UPDATE jobs SET every_s=? WHERE id=?", (int(fields["every_s"]), jid))
    con.commit()
    con.close()


def job_add(name: str, every_s: int) -> int:
    con = connect()
    cur = con.execute(
        "INSERT INTO jobs(name, every_s, enabled) VALUES (?,?,1)",
        (name, int(every_s)),
    )
    con.commit()
    jid = int(cur.lastrowid or 0)
    con.close()
    return jid


def job_touch(jid: int, err: str, ms: int) -> None:
    con = connect()
    con.execute(
        "UPDATE jobs SET last_zulu=?, last_err=?, last_ms=? WHERE id=?",
        (zulu(), (err or "")[:300], ms, jid),
    )
    con.commit()
    con.close()


def conv_new() -> int:
    con = connect()
    cur = con.execute(
        "INSERT INTO conversations(opened, title) VALUES (?,?)",
        (zulu(), "untitled"),
    )
    con.commit()
    cid = int(cur.lastrowid or 0)
    con.close()
    return cid


def conv_turn(cid: int, role: str, body: str) -> None:
    con = connect()
    con.execute(
        "INSERT INTO turns(conv, zulu, role, body) VALUES (?,?,?,?)",
        (cid, zulu(), role, (body or "")[:4000]),
    )
    con.execute("UPDATE conversations SET n_turns = n_turns + 1 WHERE id=?", (cid,))
    con.commit()
    con.close()


def conv_meta(cid: int, title: str, subject: str, words: str) -> None:
    con = connect()
    con.execute(
        "UPDATE conversations SET title=?, subject=?, words=? WHERE id=?",
        (title[:120], subject[:120], words[:300], cid),
    )
    con.commit()
    con.close()

