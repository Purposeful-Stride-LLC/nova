"""Deliberation chamber: orchestrator parks expert opinions in Tx-TEMP WHI."""

from __future__ import annotations

import json
import hashlib
from typing import Any

from nova import db, breaklog

SEATS = ("claw", "code", "brief")  # brief=qwen3:8b; no 0.5b on design


def _ensure_chunks(con) -> None:
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
        CREATE INDEX IF NOT EXISTS idx_chunks_status ON chunks(status);
        CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(hash);
        """
    )


def case_id(topic: str) -> str:
    h = hashlib.sha1((topic or "case").encode()).hexdigest()[:8]
    return f"{db.zulu().replace(':','').replace('-','')[:13]}-{h}"


def address(case: str, seat: str) -> str:
    return f"chamber/{case}/{seat}"


def store_temp(case: str, seat: str, opinion: str, cite: str = "") -> dict:
    """Park opinion as Tx-TEMP fact + optional temp chunk. Returns address."""
    seat = (seat or "").strip().lower()
    addr = address(case, seat)
    body = {
        "address": addr,
        "case": case,
        "seat": seat,
        "zulu": db.zulu(),
        "cite": cite,
        "opinion": (opinion or "")[:3500],
    }
    payload = json.dumps(body, ensure_ascii=False)
    db.put_fact("Tx-TEMP", addr, payload[:4000])
    con = db.connect()
    _ensure_chunks(con)
    hx = hashlib.sha256(payload.encode()).hexdigest()[:16]
    con.execute(
        "INSERT INTO chunks(zulu,whi,source_cite,text,hash,status) VALUES (?,?,?,?,?,?)",
        (db.zulu(), "Tx-TEMP", addr, payload[:8000], hx, "temp"),
    )
    con.commit()
    cid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.close()
    return {"ok": True, "address": addr, "chunk_id": int(cid), "whi": "Tx-TEMP"}


def list_temps(case: str) -> list[dict]:
    con = db.connect()
    rows = con.execute(
        "SELECT id,zulu,whi,title,substr(body,1,200) AS head FROM facts WHERE whi='Tx-TEMP' AND title LIKE ? ORDER BY id",
        (f"chamber/{case}/%",),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def clear_temps(case: str) -> dict:
    """Clear Tx-TEMP facts and temp chunks for a case after judgment."""
    prefix = f"chamber/{case}/%"
    con = db.connect()
    _ensure_chunks(con)
    f = con.execute("DELETE FROM facts WHERE whi='Tx-TEMP' AND title LIKE ?", (prefix,)).rowcount
    c = con.execute(
        "UPDATE chunks SET status='cleared' WHERE status='temp' AND source_cite LIKE ?",
        (prefix,),
    ).rowcount
    con.commit()
    con.close()
    db.put_fact("Ax-CHAMBER", f"cleared/{case}", json.dumps({"zulu": db.zulu(), "facts": f, "chunks": c}))
    return {"ok": True, "facts_deleted": f, "chunks_cleared": c, "case": case}


def verdict(case: str, judgment: str, orders: dict[str, Any] | None = None) -> dict:
    body = {
        "case": case,
        "zulu": db.zulu(),
        "judgment": (judgment or "")[:3000],
        "orders": orders or {},
        "temps": [t.get("title") for t in list_temps(case)],
    }
    db.put_fact("Ax-CHAMBER", f"verdict/{case}", json.dumps(body, ensure_ascii=False)[:4000])
    return body




def ask_brief(prompt: str, timeout: float = 120.0) -> str:
    """Design brief seat (qwen3:8b). Opinion only; keep_alive 0 unloads."""
    import urllib.request

    model = "qwen3:8b"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are NOVA council seat brief (qwen3:8b). "
                    "Reply under 12 lines. Agree/Amend/Defer + one risk + one next cut. "
                    "No clarifying questions. No tools."
                ),
            },
            {"role": "user", "content": (prompt or "")[:2500]},
        ],
        "stream": False,
        "keep_alive": 0,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return ((data.get("message") or {}).get("content") or "")[:3000]


def ask_small(prompt: str, timeout: float = 60.0) -> str:
    """Tiny param seat (qwen2:0.5b). Opinion only; keep_alive 0 unloads."""
    import urllib.request
    model = "qwen2:0.5b"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a tiny NOVA council seat. Reply under 8 lines. Agree/disagree + one risk. No clarifying questions. No tools."},
            {"role": "user", "content": prompt[:1800]},
        ],
        "stream": False,
        "keep_alive": 0,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return ((data.get("message") or {}).get("content") or "")[:2000]

def ask_code(prompt: str, timeout: float = 90.0) -> str:
    """codellama / Ollama seat — opinion only."""
    import urllib.request

    model = "codellama:latest"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are the llama-code expert on NOVA. Reply under 12 lines. No tools."},
            {"role": "user", "content": prompt[:2500]},
        ],
        "stream": False,
        "keep_alive": 0,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return ((data.get("message") or {}).get("content") or "")[:3000]


def ask_qwen(prompt: str) -> str:
    from nova.hands import qwen

    r = qwen.run_prompt(prompt[:1500], timeout=120)
    return (r.get("stdout") or r.get("stderr") or r.get("error") or str(r))[:3000]


def ask_claw(prompt: str) -> str:
    from nova import leash

    r = leash.openclaw_run(
        "OPINION ONLY. No file writes. Reply under 12 lines.\n" + prompt[:1500],
        session_id="nova-chamber",
        model="ollama/qwen3.5:9b",
        timeout=120,
    )
    return (r.get("text") or r.get("error") or str(r))[:3000]


def round_robin(topic: str, problem: str, seats: tuple[str, ...] | None = None) -> dict:
    """Lean MoE: default claw+code. Pass seats=("claw","qwen","code") to include qwen."""
    case = case_id(topic)
    prompt = (
        f"CASE {case}\nPROBLEM:\n{problem}\n"
        "Reply as design opinion: agree/disagree, top risk, next cut. Max 12 lines. No clarifying questions."
    )
    fn_map = {"claw": ask_claw, "qwen": ask_qwen, "code": ask_code, "small": ask_small, "brief": ask_brief}
    use = tuple(seats) if seats else SEATS
    out = {"case": case, "zulu": db.zulu(), "seats": {}, "seat_list": list(use)}
    for seat in use:
        fn = fn_map.get(seat)
        if not fn:
            continue
        try:
            opinion = fn(prompt)
            stored = store_temp(case, seat, opinion, cite=f"chamber.round:{seat}")
            out["seats"][seat] = {"ok": True, **stored, "opinion_head": opinion[:240]}
        except Exception as exc:
            breaklog.record("chamber", f"{seat}:{exc}", severity="warn", whi="Tx-TEMP")
            stored = store_temp(case, seat, f"ERROR: {exc}", cite="chamber.error")
            out["seats"][seat] = {"ok": False, **stored, "error": str(exc)}
    return out


def council(topic: str, steward_report: str, seats: tuple[str, ...] | None = None) -> dict:
    """Steward briefing -> lean round_robin. Default claw+code (pruned spine)."""
    return round_robin(topic, steward_report, seats=seats)


def session_motions(
    motions: list[dict],
    seats: tuple[str, ...] | None = None,
) -> dict:
    """Roberts-style AI council: each motion in order; each seat loads, opines, unloads (keep_alive 0).

    motions: [{id, title, problem}]  problem includes steward brief + sub-questions.
    Returns {session, motions: [{id, case, seats...}], zulu}.
    """
    use = tuple(seats) if seats else SEATS
    fn_map = {"claw": ask_claw, "qwen": ask_qwen, "code": ask_code, "small": ask_small, "brief": ask_brief}
    session = case_id("roberts-session")
    out = {"session": session, "zulu": db.zulu(), "seat_list": list(use), "motions": []}
    for m in motions:
        mid = m.get("id") or "M"
        title = m.get("title") or mid
        problem = m.get("problem") or ""
        case = case_id(f"{session}-{mid}")
        prompt = (
            f"SESSION {session}\nMOTION {mid}: {title}\n"
            f"RULES: Opinion only. Max 10 lines. No clarifying questions. "
            f"State: Agree / Amend / Oppose, then one risk, then one next cut.\n"
            f"BRIEF:\n{problem[:2200]}"
        )
        entry = {"id": mid, "title": title, "case": case, "seats": {}}
        for seat in use:
            fn = fn_map.get(seat)
            if not fn:
                continue
            try:
                opinion = fn(prompt)
                stored = store_temp(case, seat, opinion, cite=f"roberts:{mid}:{seat}")
                entry["seats"][seat] = {"ok": True, **stored, "opinion": opinion[:1500]}
            except Exception as exc:
                breaklog.record("chamber", f"{mid}:{seat}:{exc}", severity="warn", whi="Tx-TEMP")
                stored = store_temp(case, seat, f"ERROR: {exc}", cite="roberts.error")
                entry["seats"][seat] = {"ok": False, **stored, "error": str(exc)}
        out["motions"].append(entry)
        db.put_fact("Ax-CHAMBER", f"motion/{session}/{mid}", json.dumps({
            "title": title, "case": case, "seats": list(entry["seats"].keys())
        })[:4000])
    return out


