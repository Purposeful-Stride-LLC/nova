"""Scheduler. TUI edits the jobs table. Daemon ticks it."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from nova import db

_LAST: dict[int, float] = {}


def due(now: float | None = None) -> list[dict]:
    now = now or time.time()
    out = []
    for row in db.jobs():
        if not row.get("enabled"):
            continue
        prev = _LAST.get(row["id"], 0)
        if now - prev >= max(15, int(row["every_s"] or 60)):
            out.append(row)
    return out


def mark(jid: int) -> None:
    _LAST[jid] = time.time()


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
            note = f"probes={len(sw.get('probes') or [])}"
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
    return f"convs={n}"


def whistle() -> str:
    import random

    from nova import office, pocket

    office._ensure()
    crew = office.staff()
    emp = random.choice(crew) if crew else {"id": "hearth@local", "voice": "anna"}
    line = random.choice(
        [
            "Still here. Offline. Private.",
            "Queue is law.",
            "Have you eaten, biologic.",
            "Palace holds.",
        ]
    )
    try:
        pocket.speak(line, emp.get("voice") or "anna")
    except Exception as exc:
        return f"tts {exc}"
    office.bump(emp.get("id") or "hearth@local", "jobs_run")
    return f"{emp.get('id')} {line}"


def tick() -> list[dict]:
    ran = []
    for row in due():
        mark(row["id"])
        res = run_named(row["name"])
        db.job_touch(row["id"], res.get("err") or "", res.get("ms") or 0)
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

