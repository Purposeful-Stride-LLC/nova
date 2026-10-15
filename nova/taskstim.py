"""Task stimulus (fieldkit 2.1): keep NOVA on task.

Reads (read-only, mode=ro): open HIL reports, URLs awaiting approval, pending docs, failed packets,
stale checks (enabled jobs not run within 3x cadence), pending inbox proposals. Produces:
- NOW lines (data/run/task_now.json) that the chat NOW block shows as "TASK" lines;
- proposed next tasks in the command inbox (source=task-stimulus). Proposals go to HIL:
  they are never executed until the operator approves them.
"""
from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime, timezone

from nova.ctime import parse_zulu

STALE_FACTOR = 3
MAX_PROPOSALS = 3


def _ro():
    from nova import db, selfknow
    return selfknow.ro_connect(db.db_path())


def gather(now: float | None = None) -> dict:
    now = now or time.time()
    g: dict = {"reports_open": None, "report_top": [], "urls_waiting": [], "docs_pending": None,
               "packets_fail": None, "stale": []}
    try:
        con = _ro()
    except Exception as exc:
        g["error"] = str(exc)[:120]
        return g
    try:
        rows = con.execute("SELECT id, rank, title FROM reports WHERE status='open' ORDER BY rank DESC, id DESC").fetchall()
        g["reports_open"] = len(rows)
        norm = Counter((t or "").split(":")[0].strip()[:40] for _, _, t in rows)
        g["report_top"] = norm.most_common(3)
        g["oldest_top_report"] = [int(r[0]) for r in rows[:3]]
        g["urls_waiting"] = [int(r[0]) for r in con.execute(
            "SELECT id FROM queue WHERE status IN ('queued','pending') AND description LIKE 'http%' ORDER BY id LIMIT 5")]
        try:
            g["docs_pending"] = con.execute("SELECT count(*) FROM docs_queue WHERE status IN ('queued','pending')").fetchone()[0]
        except Exception:
            g["docs_pending"] = None
        g["packets_fail"] = con.execute("SELECT count(*) FROM packets WHERE status='fail'").fetchone()[0]
        for jid, name, every, en, last in con.execute("SELECT id, name, every_s, enabled, last_zulu FROM jobs ORDER BY id"):
            if not en:
                continue
            t = parse_zulu(last) if last else None
            age = (now - t.timestamp()) if t else None
            if age is None or age > STALE_FACTOR * max(60, int(every or 60)):
                g["stale"].append({"id": int(jid), "name": name, "age_min": None if age is None else int(age // 60)})
    finally:
        con.close()
    return g


def lines(g: dict) -> list[str]:
    out = []
    if g.get("reports_open") is not None:
        top = ", ".join(f"{k} x{n}" for k, n in g.get("report_top") or [])
        out.append(f"TASK {g['reports_open']} HIL reports open" + (f" (most: {top})" if top else "") + ".")
    if g.get("urls_waiting"):
        out.append(f"TASK {len(g['urls_waiting'])} URLs wait for operator approval (ids {', '.join(map(str, g['urls_waiting']))}).")
    if g.get("docs_pending"):
        out.append(f"TASK {g['docs_pending']} docs pending ingest.")
    if g.get("packets_fail"):
        out.append(f"TASK {g['packets_fail']} failed packets need review.")
    for s in g.get("stale") or []:
        a = "never run" if s["age_min"] is None else f"last run {s['age_min']} min ago"
        out.append(f"TASK stale check: {s['name']} #{s['id']} ({a}).")
    return out[:8]


def proposals(g: dict) -> list[tuple[str, dict, str]]:
    props = []
    for s in (g.get("stale") or [])[:2]:
        props.append(("job.run_now", {"id": s["id"]}, f"stale check {s['name']}"))
    if g.get("reports_open"):
        top = (g.get("report_top") or [("reports", 0)])[0]
        props.append(("task.note", {"topic": "triage reports", "group": top[0], "count": g["reports_open"]},
                      f"triage {g['reports_open']} open reports, start with '{top[0]}' x{top[1]}"))
    return props[:MAX_PROPOSALS]


def run(now: float | None = None, propose: bool = True) -> dict:
    from nova import cmdinbox, db
    g = gather(now)
    nl = lines(g)
    n_new = n_dup = 0
    if propose:
        for verb, args, why in proposals(g):
            r = cmdinbox.propose(verb, args, source="task-stimulus", why=why)
            if r.get("duplicate"):
                n_dup += 1
            elif r.get("ok"):
                n_new += 1
    rec = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "now": nl,
           "pending": len(cmdinbox.listing("proposed"))}
    d = db.home() / "data" / "run"
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "task_now.tmp"
    tmp.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    os.replace(tmp, d / "task_now.json")
    return {**rec, "proposed": n_new, "duplicates": n_dup}


def read_now(max_age_s: int = 3600) -> list[str]:
    """For the NOW block. Old or missing file -> [] (never stale TASK lines)."""
    from nova import db
    try:
        rec = json.loads((db.home() / "data" / "run" / "task_now.json").read_text(encoding="utf-8"))
        t = parse_zulu(rec.get("generated"))
        if t and (time.time() - t.timestamp()) <= max_age_s:
            return list(rec.get("now") or [])
    except Exception:
        pass
    return []
