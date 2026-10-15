"""Command inbox (file IPC) for NOVA 2.1. GUI, chat and task-stimulus PROPOSE; the operator
APPROVES; only the daemon EXECUTES approved commands. Nothing is auto-applied.

Layout under <NOVA_HOME>/data/commands/: proposed/ approved/ done/ denied/ — one JSON per command,
moved atomically (os.replace) between folders. The GUI never writes NOVA.db: its "approve" click
writes approved/<id>.json and the daemon performs the DB write on its next tick (closes the
GUI approve -> board.drain_one gap: url.approve sets queue status 'approved', which is the only
status board.drain_one drains).
"""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path

STATES = ("proposed", "approved", "done", "denied")
VERBS = {
    "job.pause": "disable a job (args: id)",
    "job.resume": "enable a job (args: id)",
    "job.run_now": "run a job on the next tick (args: id)",
    "report.approve": "set one HIL report to approved (args: id)",
    "report.close": "set one HIL report to closed (args: id)",
    "url.approve": "approve one queued URL for board drain (args: id)",
    "url.deny": "deny one queued URL (args: id)",
    "chamber.promote": "promote chamber opinions for a case into live RAG (args: case)",
    "selfimprove.apply": "apply an approved self-improve proposal to the sandbox (args: pid)",
    "url.enqueue": "queue a URL for approval (args: url); drain still needs url.approve + net_allowlist",
    "reports.approve_all": "bulk-approve open HIL reports (operator only, confirmed)",
    "ingest.clear_standing": "clear standing ingest with DB backup (operator only, confirmed)",
    "mail.deliver": "deliver up to N queued packets (args: n)",
    "task.note": "informational next-task suggestion; executing it only records an ack",
}


def root() -> Path:
    from nova import db
    r = db.home() / "data" / "commands"
    for s in STATES:
        (r / s).mkdir(parents=True, exist_ok=True)
    return r


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write(state: str, rec: dict) -> Path:
    p = root() / state / f"{rec['id']}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=True), encoding="utf-8")
    os.replace(tmp, p)
    return p


def _move(src: Path, state: str, rec: dict) -> Path:
    """Rewrite the record in place, then atomically MOVE it to the new state folder (no deletes)."""
    tmp = src.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=True), encoding="utf-8")
    os.replace(tmp, src)
    dst = root() / state / src.name
    os.replace(src, dst)
    return dst


def _find(cid: str) -> tuple[str, Path] | None:
    for s in STATES:
        p = root() / s / f"{cid}.json"
        if p.is_file():
            return s, p
    return None


def listing(state: str = "proposed") -> list[dict]:
    out = []
    for p in sorted((root() / state).glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def pending_same(verb: str, args: dict) -> dict | None:
    for s in ("proposed", "approved"):
        for r in listing(s):
            if r.get("verb") == verb and r.get("args") == args:
                return r
    return None


def propose(verb: str, args: dict | None = None, *, source: str = "operator", why: str = "") -> dict:
    """Queue a proposal. Unknown verbs are refused (fail closed). Duplicates return the pending one."""
    args = dict(args or {})
    if verb not in VERBS:
        return {"ok": False, "refused": True, "error": f"unknown verb {verb}"}
    if source == "chat":
        from nova import gates
        g = gates.chat_command_allowed(verb)
        if not g["allow"]:
            return {"ok": False, "refused": True, "error": g["reason"]}
    dup = pending_same(verb, args)
    if dup:
        return {"ok": True, "duplicate": True, **dup}
    rec = {"id": time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + "-" + secrets.token_hex(3),
           "verb": verb, "args": args, "source": source, "why": why[:300],
           "proposed": _now(), "state": "proposed"}
    _write("proposed", rec)
    return {"ok": True, **rec}


def approve(cid: str, by: str = "operator") -> dict:
    """Operator release. Moves proposed -> approved. The daemon executes on its next tick."""
    f = _find(cid)
    if not f or f[0] != "proposed":
        return {"ok": False, "error": f"not proposed: {cid}"}
    rec = json.loads(f[1].read_text(encoding="utf-8"))
    rec.update(state="approved", approved=_now(), approved_by=by)
    _move(f[1], "approved", rec)
    return {"ok": True, **rec}


def operator_command(verb: str, args: dict, by: str = "gui") -> dict:
    """A direct operator action (confirmed in the GUI): propose + approve in one step."""
    r = propose(verb, args, source=by, why="operator action")
    if not r.get("ok") or r.get("state") != "proposed":
        return r
    return approve(r["id"], by=by)


def deny(cid: str, by: str = "operator") -> dict:
    f = _find(cid)
    if not f or f[0] != "proposed":
        return {"ok": False, "error": f"not proposed: {cid}"}
    rec = json.loads(f[1].read_text(encoding="utf-8"))
    rec.update(state="denied", denied=_now(), denied_by=by)
    _move(f[1], "denied", rec)
    return {"ok": True, **rec}


# ---------------------------------------------------------------- daemon side

def _exec(rec: dict) -> dict:
    from nova import db
    v, a = rec["verb"], rec.get("args") or {}
    if v in ("job.pause", "job.resume"):
        db.job_set(int(a["id"]), enabled=0 if v == "job.pause" else 1)
        return {"ok": True}
    if v == "job.run_now":
        from nova import sched
        sched.request_run_now(int(a["id"]))
        return {"ok": True}
    if v in ("report.approve", "report.close"):
        st = "approved" if v == "report.approve" else "closed"
        con = db.connect()
        n = con.execute("UPDATE reports SET status=? WHERE id=? AND status='open'", (st, int(a["id"]))).rowcount
        con.commit()
        con.close()
        return {"ok": n == 1, "rows": n}
    if v in ("url.approve", "url.deny"):
        st = "approved" if v == "url.approve" else "denied"
        con = db.connect()
        n = con.execute("UPDATE queue SET status=? WHERE id=? AND status IN ('queued','pending')",
                        (st, int(a["id"]))).rowcount
        con.commit()
        con.close()
        return {"ok": n == 1, "rows": n}
    if v == "chamber.promote":
        from nova import chamber
        return chamber.promote_to_rag(str(a["case"]))
    if v == "selfimprove.apply":
        from nova import selfimprove
        return selfimprove.apply(str(a["pid"]), approved_cmd=rec["id"])
    if v == "url.enqueue":
        from nova import board
        return {"ok": True, "queue_id": board.enqueue_url(str(a["url"]))}
    if v == "reports.approve_all":
        from nova import office
        return {"ok": True, **office.approve_all(reports=True, board_queue=False)}
    if v == "ingest.clear_standing":
        from nova import office
        r = office.clear_standing_ingest(dry_run=False, backup=True)
        return {"ok": True, **{k: str(r.get(k)) for k in ("docs_queue", "board_urls", "packets", "fs_waiting", "backup")}}
    if v == "mail.deliver":
        from nova import office
        return {"ok": True, "n": len(office.deliver_inbox(int(a.get("n", 3))))}
    if v == "task.note":
        return {"ok": True, "ack": True}
    return {"ok": False, "error": "unknown verb"}


def execute_approved(limit: int = 10) -> list[dict]:
    """Daemon only. Executes approved commands, logs each to master_log, moves them to done/."""
    from nova import db
    out = []
    for rec in listing("approved")[:limit]:
        t0 = db.zulu()
        try:
            res = _exec(rec)
        except Exception as exc:
            res = {"ok": False, "error": str(exc)[:200]}
        rec.update(state="done", done=_now(), result=res)
        _move(root() / "approved" / f"{rec['id']}.json", "done", rec)
        try:
            db.log("cmd:" + rec["verb"], t0, db.zulu(), 0, "" if res.get("ok") else str(res.get("error") or "failed"),
                   f"id={rec['id']} args={rec.get('args')} by={rec.get('approved_by')}")
        except Exception:
            pass
        out.append(rec)
    return out
