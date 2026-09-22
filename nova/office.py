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
            "queued",
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
