"""Interactive ingest + job board. Daemon drains; GUI/TUI enqueue."""

from __future__ import annotations

from nova import db


def enqueue_url(url: str) -> int:
    url = (url or "").strip()
    if not url.startswith("http"):
        raise ValueError("need http(s) url")
    con = db.connect()
    cur = con.execute(
        "INSERT INTO queue(zulu, description, risk, status) VALUES (?,?,?,?)",
        (db.zulu(), url, "low", "queued"),
    )
    con.commit()
    jid = int(cur.lastrowid or 0)
    con.close()
    return jid


def drain_one() -> dict:
    con = db.connect()
    row = con.execute(
        "SELECT * FROM queue WHERE status='queued' AND description LIKE 'http%' ORDER BY id LIMIT 1"
    ).fetchone()
    if not row:
        con.close()
        return {"ok": True, "empty": True}
    rec = dict(row)
    con.execute("UPDATE queue SET status='running' WHERE id=?", (rec["id"],))
    con.commit()
    con.close()
    from nova.hands import web

    res = web.fetch(rec["description"])
    con = db.connect()
    con.execute(
        "UPDATE queue SET status=? WHERE id=?",
        ("done" if res.get("ok") else "fail", rec["id"]),
    )
    con.commit()
    con.close()
    return {"ok": True, "id": rec["id"], "url": rec["description"], "fetch": res}


def pending_urls() -> list[dict]:
    con = db.connect()
    rows = con.execute(
        "SELECT * FROM queue WHERE description LIKE 'http%' ORDER BY id DESC LIMIT 20"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]
