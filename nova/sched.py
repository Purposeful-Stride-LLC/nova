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
    try:
        arts = sorted((db.home() / "data" / "artifacts").glob("tts_*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        purged = 0
        for oldw in arts[25:]:
            oldw.unlink(missing_ok=True)
            purged += 1
    except Exception:
        purged = -1
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

