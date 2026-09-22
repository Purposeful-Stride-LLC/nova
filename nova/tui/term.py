"""NOVA Terminal 1.4 — edits the same jobs table the daemon ticks."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import urllib.request

from nova import db, forge, holmes, ollama_talk, parser, pocket, router, sched, tools, tutorial
from nova.hands import codesum, history, pdf, web
from nova.masks import MASKS, apply, listing, pick_mask, limits_for, pick_mask, limits_for

W, H = shutil.get_terminal_size(fallback=(100, 32))
WIDTH = max(72, min(W, 140))
HELP = """/help /tutorial [n] /tools /suggest
/jobs /job add SECS name /job on ID /job off ID /tick
/web URL  /crawl URL  /hunt Q  /pdf PATH  /codesum PATH
/rag QUERY  /chamber TOPIC  /claw [msg]  /qwen [msg]  /snap
/models /model NAME
/mask NAME|list|auto   (masks not jackets; auto = activation words)
/conv new  /holmes /sherlock  /queue /approve N /deny N
/reports /ack ID /staff /history
/tts TEXT /voice ID /cam [n] /see [n|PATH] /hear WAV /ask TEXT
/msg ...  /wa status|draft|send|link
/quit

Masks: brief hearth tutor deleo sentinel chronicler reviewer economist
       seer ear openclaw qwen clerk grokbot
Parser: [speak anna] one short sentence [/speak]
"""


def _cls():
    sys.stdout.write("\033[H\033[J")


state = {
    "hist": [],
    "art": ["ARTIFACT"],
    "model": os.environ.get("NOVA_MODEL", "llama3-groq-tool-use:8b"),
    "mask": "brief",
    "mask_auto": False,
    "voice": "anna",
    "conv": None,
}


def say(role, text):
    state["hist"].append(f"{role}: {text}")
    if state["conv"]:
        db.conv_turn(state["conv"], role, text)
    log = db.home() / "data" / "chat.log"
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{db.zulu()} {role}: {text}\n")


def art(*rows):
    state["art"] = [str(r)[:40] for r in rows]


def _wrap_line(text: str, width: int) -> list[str]:
    text = (text or "").replace("\t", " ")
    if width < 8:
        return [text[:width]]
    out = []
    for raw in (text or "").splitlines() or [""]:
        s = raw
        while len(s) > width:
            cut = s.rfind(" ", 0, width)
            if cut < width // 3:
                cut = width
            out.append(s[:cut].rstrip())
            s = s[cut:].lstrip()
        out.append(s)
    return out or [""]


def draw():
    left_w = int(WIDTH * 0.62)
    right_w = WIDTH - left_w - 3
    lines = ["╔" + "═" * (WIDTH - 2) + "╗"]
    lines.append("║" + f" NOVA 1.7  conv={state['conv']}  {state['mask']} {state['model'][:18]} ".center(WIDTH - 2)[: WIDTH - 2].ljust(WIDTH - 2) + "║")
    lines.append("╠" + "═" * (WIDTH - 2) + "╣")
    wrapped = []
    for row in state["hist"]:
        wrapped.extend(_wrap_line(row, max(8, left_w - 1)))
    chat = wrapped[-12:]
    while len(chat) < 12:
        chat.append("")
    for i in range(12):
        L = (" " + chat[i])[:left_w].ljust(left_w)
        R = (state["art"][i] if i < len(state["art"]) else "")[:right_w].ljust(right_w)
        lines.append("║" + L + "│" + R + "║")
    lines.append("╚" + "═" * (WIDTH - 2) + "╝")
    _cls()
    print("\n".join(lines))
    print(">> ", end="", flush=True)


def ask(text):
    hits = db.hunt(text)
    ctx = "\n".join(f"{h.get('whi')} {h.get('title')} src={h.get('source_url')}" for h in hits)
    model = router.pick(text, state["model"])
    if state.get("mask_auto"):
        state["mask"] = pick_mask(text)
    sys_p = apply(state["mask"]) + "\n" + parser.GRAMMAR + "\nPalace hits:\n" + (ctx or "(none)")
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": text},
            ],
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode())
        raw_out = (data.get("message") or {}).get("content") or data.get("response") or ""
        visible, spoken = parser.peel(raw_out)
        for voice, line in spoken:
            try:
                res = pocket.speak(line, voice)
                if not res.get("ok"):
                    art("TTS-FAIL", f"{voice}: {str(res)[:180]}")
            except Exception as exc:
                art("TTS-FAIL", f"{voice}: {exc}")
        return visible or raw_out
    except Exception as exc:
        return f"[ollama] {exc}"


def handle(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return
    low = raw.lower()
    if low in {"/quit", "quit", "exit"}:
        raise SystemExit
    if low in {"/list", "list"}:
        handle("/tools")
        return
    if re.search(r"tutorial|next page|page\s*\d+", low) and not low.startswith("/ask"):
        m = re.search(r"(\d+)", low)
        handle("/tutorial " + (m.group(1) if m else "2"))
        return
    if low in {"/help", "help"}:
        say("NOVA", HELP)
        art(*HELP.split("\n"))
        return
    if low.startswith("/tutorial"):
        n = 1
        parts = raw.split()
        if len(parts) > 1 and parts[1].isdigit():
            n = int(parts[1])
        text = tutorial.page(n)
        say("NOVA", text)
        art(*text.split("\n"))
        return
    if low == "/tools":
        text = tools.listing()
        say("NOVA", text)
        art("TOOLS", *text.split("\n")[:10])
        return
    if low == "/forge":
        text = forge.listing()
        say("NOVA", text)
        art("FORGE", *[t["job"] for t in forge.FORGE])
        return
    if low == "/suggest":
        rows = tools.suggested_jobs()
        for name, secs, why in rows:
            say("NOVA", f"/job add {secs} {name}  # {why}")
        art("SUGGEST", *[f"{s}s {n}" for n, s, _ in rows])
        return
    if low.startswith("/history"):
        art("HIST", str(history.ingest()))
        return
    if low.startswith("/pdf"):
        path = raw.split(None, 1)[1] if " " in raw else ""
        art("PDF", str(pdf.ingest(path)))
        return
    if low.startswith("/history"):
        art("HIST", str(history.ingest()))
        return
    if low.startswith("/codesum"):
        path = raw.split(None, 1)[1] if " " in raw else "."
        art("CODESUM", str(codesum.run(path, state["model"])))
        return
    if low == "/queue":
        qrows = db.queue_rows()
        art("QUEUE", *[f"{r['id']} {r['status']} {r['description']}" for r in qrows] or ["empty"])
        return
    if low.startswith("/approve"):
        db.set_queue(int(raw.split()[1]), "approved")
        handle("/queue")
        return
    if low.startswith("/deny"):
        db.set_queue(int(raw.split()[1]), "denied")
        handle("/queue")
        return
    if low.startswith("/voice"):
        state["voice"] = pocket.resolve_voice(raw.split(None, 1)[1] if " " in raw else "anna")
        return
    if low == "/reports":
        from nova import office

        rows = office.reports()
        art("REPORTS", *[f"{r['id']} r{r['rank']} {r['status']} {r['title']}" for r in rows] or ["none open"])
        return
    if low.startswith("/ack"):
        from nova import office

        office.stamp_report(int(raw.split()[1]), "acked")
        handle("/reports")
        return
    if low == "/staff":
        from nova import office

        rows = office.staff()
        art("STAFF", *[f"{r['id']} v={r['voice']} jobs={r['jobs_run']} acc={r['accepted']}" for r in rows])
        return
    if low.startswith("/see"):
        from nova import senses

        arg = raw.split(None, 1)[1] if " " in raw else "0"
        if arg.isdigit():
            art("SEE", str(senses.save_still(int(arg))))
        else:
            art("VLM", str(senses.describe(arg)))
        return
    if low.startswith("/hear"):
        from nova import senses

        path = raw.split(None, 1)[1] if " " in raw else ""
        art("HEAR", str(senses.wav_features(path)))
        return
    if low == "/vision":
        from nova import senses

        art("VTAGS", *senses.vision_tags() or ["none — ollama pull moondream"])
        return
    if low.startswith("/cam"):
        from nova.hands import cameras

        arg = raw.split(None, 1)[1] if " " in raw else "0"
        art("CAM", str(cameras.snapshot(int(arg) if str(arg).isdigit() else 0)))
        return
    if low == "/jobs":
        rows = db.jobs()
        art("JOBS", *[f"{r['id']} {r['name']} {r['every_s']}s en={r['enabled']} {r.get('last_err') or ''}" for r in rows])
        return
    if low.startswith("/job add"):
        parts = raw.split()
        # /job add 60 holmes
        try:
            jid = db.job_add(parts[3], int(parts[2]))
            art("JOB ADD", str(jid))
        except Exception as exc:
            art("JOB ADD", str(exc))
        return
    if low.startswith("/job on"):
        db.job_set(int(raw.split()[2]), enabled=1)
        handle("/jobs")
        return
    if low.startswith("/job off"):
        db.job_set(int(raw.split()[2]), enabled=0)
        handle("/jobs")
        return
    if low == "/holmes":
        sw = holmes.sweep()
        art("HOLMES", str(sw.get("duration_s")), *[p.get("source") for p in sw.get("probes", [])])
        return
    if low.startswith("/rag"):
        from nova import rag

        rest = raw[4:].strip()
        if not rest:
            return "usage: /rag QUERY"
        return str(rag.retrieve(rest, limit=4))[:1200]

    if low.startswith("/crawl"):
        from nova import crawl as crawlmod

        rest = raw[6:].strip()
        if not rest.startswith("http"):
            return "usage: /crawl https://URL   (daemon: crawl:URL or /job add)"
        return str(crawlmod.crawl(rest, max_pages=3, max_depth=2))[:800]

    if low.startswith("/web"):
        url = raw.split(None, 1)[1] if " " in raw else ""
        res = web.fetch(url)
        art("WEB", "ingest="+str(res.get("ingested")), str(res.get("matrix", {}).get("score")), res.get("whi") or res.get("error"))
        say("NOVA", json.dumps({k: res[k] for k in res if k != "matrix"} | {"score": (res.get("matrix") or {}).get("score")}, default=str)[:500])
        return
    if low.startswith("/hunt"):
        q = raw.split(None, 1)[1] if " " in raw else ""
        hits = db.hunt(q)
        art("HUNT", *[f"{h.get('whi')} {h.get('title')}" for h in hits] or ["none"])
        return
    if low == "/models":
        art("MODELS", *router.catalog() or ["none"])
        return
    if low.startswith("/model"):
        state["model"] = raw.split(None, 1)[1] if " " in raw else state["model"]
        art("MODEL", state["model"])
        return
    if low.startswith("/mask"):
        rest = raw.split(None, 1)[1] if " " in raw else ""
        rlow = rest.strip().lower()
        if rlow in {"", "list"}:
            art("MASKS", listing())
            return
        if rlow == "auto":
            state["mask_auto"] = True
            art("MASK", "auto on ? activation words pick the seat")
            return
        if rlow in {"auto off", "manual"}:
            state["mask_auto"] = False
            art("MASK", "auto off")
            return
        name = rlow
        state["mask"] = name if name in MASKS else "brief"
        state["mask_auto"] = False
        art("MASK", state["mask"], str(limits_for(state["mask"])))
        return

    if low.startswith("/chamber"):
        from nova import chamber
        import json

        rest = raw[8:].strip()
        if rest.startswith("clear "):
            return str(chamber.clear_temps(rest[6:].strip()))
        if rest.startswith("list "):
            return str(chamber.list_temps(rest[5:].strip()))[:800]
        return "usage: /chamber list CASE | /chamber clear CASE"

    if low.startswith("/snap"):
        from nova import snap as snapmod

        rest = raw[5:].strip()
        return str(snapmod.snap(rest or "tui snap"))[:400]

    if low.startswith("/qwen"):
        from nova.hands import qwen as qwen_hand

        rest = raw[5:].strip()
        if not rest:
            return "usage: /qwen PROMPT"
        return str(qwen_hand.run_prompt(rest))[:1200]

    
    if low.startswith("/wa") or low.startswith("/msg"):
        from nova import msg as nova_msg
        parts = raw.split(None, 2)
        sub = (parts[1].lower() if len(parts) > 1 else "status")
        if sub in ("status", "st"):
            return str(nova_msg.status())
        if sub in ("link", "qr", "login"):
            return str(nova_msg.link_qr(new_window=True))
        if sub == "draft":
            body = parts[2] if len(parts) > 2 else ""
            return str(nova_msg.draft(body))
        if sub == "send":
            # /wa send APPROVE text...   or /wa send dry text...
            rest = parts[2] if len(parts) > 2 else ""
            bits = rest.split(None, 1)
            flag = (bits[0].lower() if bits else "")
            body = bits[1] if len(bits) > 1 else ""
            if flag == "approve":
                return str(nova_msg.send(body, approve=True))
            if flag == "dry":
                return str(nova_msg.send(body, dry_run=True))
            return "usage: /wa status | /wa link | /wa draft TEXT | /wa send dry TEXT | /wa send approve TEXT"
        return "usage: /wa status | /wa link | /wa draft TEXT | /wa send dry TEXT | /wa send approve TEXT"

    if low.startswith("/claw"):
        from nova import claw

        rest = raw[5:].strip()
        if not rest:
            return str(claw.status())[:800]
        return str(claw.ask(rest))[:1200]

    if low.startswith("/tts"):
        art("TTS", str(pocket.speak(raw.split(None, 1)[1] if " " in raw else "", state["voice"])))
        return
    if low in {"/bites", "/queue-bites"}:
        from nova import bites

        rows = bites.queued(12)
        art("BITES", *[f"{r['id']} {r['status']} {r['worker']} {r['line'][:28]}" for r in rows] or ["empty"])
        return
    if low in {"/play", "/bite"}:
        from nova import bites

        art("PLAY", str(bites.play_next()))
        return
    if low.startswith("/sherlock"):
        from nova import sherlock

        target = raw.split(None, 1)[1] if " " in raw else "nova"
        art("SHERLOCK", str(sherlock.run(target)["kinds"]))
        return
    if low == "/tick":
        art("TICK", *[str(r) for r in sched.tick()] or ["nothing due"])
        return
    say("YOU", raw)
    reply = ask(raw)
    say("NOVA", reply)


def main():
    if not sys.stdout.isatty():
        print("Need a real console. python -m nova.tui")
        return
    if os.name == "nt":
        os.system("")
    db.connect().close()
    if not os.environ.get("NOVA_NOSPLASH"):
        from nova import splash

        splash.run(15, sound=True)
    say("NOVA", f"1.7 attach. db={db.db_path()}. /help")
    draw()
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        try:
            handle(line)
        except SystemExit:
            break
        except Exception as exc:
            say("NOVA", f"[tool error] {exc}")
        draw()
    print("detach")
