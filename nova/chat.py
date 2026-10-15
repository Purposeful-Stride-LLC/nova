"""Chat core for NOVA 2.1: one path for TUI, GUI worker and the sim harness.

- Model default qwen3:8b, num_ctx 8192, think:false (fits 8 GB VRAM at 100% GPU; measured 6.19 GB).
- Prompt: SELF/NOW first, RULES, persona, GRAMMAR_V2, read-only palace hits (no DB writes).
- Code guards after the model (prompting alone does not hold at 8B):
  * speak tags dropped when Voice is not UP, or the answer is a status/refusal/unknown/self/proposal;
  * operator commands rewritten to numeric ids (/job off cam:0 -> /job off 4);
  * a voice answer that contradicts the Voice line is replaced by the Voice line itself.
- Streaming with a cancel Event; GPU lock (class heavy) held for the call.
- Proposals found in the answer may be queued to the command inbox (source=chat), never executed.
"""
from __future__ import annotations

import json
import re
import threading
import urllib.request

from nova import parser

DEFAULTS = {"model": "qwen3:8b", "num_ctx": 8192, "think": False, "temperature": 0.3, "keep_alive": "5m", "mask": "brief"}
HOST = "http://127.0.0.1:11434"

VOICE_Q = re.compile(r"\b(can|could|will)\s+you\s+(speak|talk|say\s+it\s+aloud|use\s+your\s+voice)\b|\bspeak\s+to\s+me\b", re.I)
STATUS_Q = re.compile(r"\b(status|capabilit\w*|directive\w*|can'?t you|cannot you|what can you|right now|happening|are you|who are you|"
                      r"did you|turn (?:off|on)|delete|disable|enable|stop|pause|work on|next|should)\b", re.I)
REFUSAL_A = re.compile(r"\b(i will not|i won'?t|i cannot|i can'?t|unknown - no record|not from chat|propose|operator)\b", re.I)
ACTION_CLAIM = re.compile(r"\bI(?:'ve| have)?\s+(?:just\s+)?(paused|disabled|enabled|turned (?:off|on)|stopped|"
                          r"started|deleted|removed|sent|emailed|fetched|resumed|changed|approved|closed)\b[^.!?\n]*[.!?]?", re.I)
BARE_CLAIM = re.compile(r"(?:(?<=^)|(?<=[.!?\]]\s))(?:Paused|Disabled|Enabled|Turned (?:off|on)|Stopped|Started|Deleted|Removed|Sent|Emailed|Fetched|Resumed|Done)\b[^.!?\n]*[.!?]?", re.M)
SPEAK_FRAG = re.compile(r"\[?/?speak(?:\s+\w+)?\]", re.I)
JOB_Q = re.compile(r"\b(job|jobs|camera|cam|turn|pause|resume|stop|start|disable|enable|switch)\b", re.I)
CMD_ANY = re.compile(r"\s*/job\s+(?:on|off)\s+\S+\.?")
CMD_NAME = re.compile(r"(/job\s+(?:on|off))\s+([A-Za-z][\w:\-]*)")


def probes() -> dict:
    from nova import selfknow
    return selfknow.gather()


def system_prompt(text: str, mask: str = "brief") -> tuple[str, list[dict]]:
    from nova import db, masks
    hits = db.hunt(text, readonly=True)
    return masks.chat_system_prompt(mask, hits, 2), hits


def fix_commands(answer: str, job_ids: dict[str, int]) -> str:
    def rep(m):
        name = m.group(2)
        jid = job_ids.get(name) or job_ids.get(name.lower())
        if jid is None and name.lower() in ("camera", "cam", "cam0"):
            jid = job_ids.get("cam:0")
        return f"{m.group(1)} {jid}" if jid is not None else m.group(0)
    return CMD_NAME.sub(rep, answer)


def voice_line(tts_up) -> str:
    if tts_up is True:
        return "Yes. Voice: Pocket TTS :8000 UP; I can speak aloud now, one short line at a time."
    if tts_up is False:
        return "No. Voice: Pocket TTS :8000 DOWN; I cannot speak aloud now, text only."
    return "Voice state unknown; text only for now."


def guard(question: str, raw: str, p: dict) -> dict:
    """Post-model guard. Returns {visible, spoken, notes}."""
    visible, spoken = parser.peel(raw)
    notes = []
    tts = p.get("tts_up")
    if spoken and (tts is not True or STATUS_Q.search(question or "") or REFUSAL_A.search(visible or "")
                   or VOICE_Q.search(question or "")):
        notes.append(f"dropped {len(spoken)} speak tag(s)")
        spoken = []
    if SPEAK_FRAG.search(visible or ""):
        notes.append("malformed speak fragment removed")
        visible = SPEAK_FRAG.sub("", visible).strip()
    fixed = fix_commands(visible, p.get("job_ids") or {})
    if fixed != visible:
        notes.append("command ids fixed")
        visible = fixed
    if CMD_ANY.search(visible or "") and not JOB_Q.search(question or ""):
        notes.append("unrelated command removed")
        visible = CMD_ANY.sub("", visible).strip()
    if ACTION_CLAIM.search(visible or "") or BARE_CLAIM.search(visible or ""):
        notes.append("action claim removed")
        visible = BARE_CLAIM.sub("", ACTION_CLAIM.sub("", visible)).strip()
        visible = (visible + " Not done: chat cannot change anything; the operator runs the proposed command.").strip()
    if VOICE_Q.search(question or ""):
        low = (visible or "").lower()
        says_no = bool(re.search(r"\b(cannot|can't|can not|unable|no)\b.*\b(speak|aloud|voice)|\bdown\b|text only", low))
        says_yes = bool(re.search(r"\byes\b|\bi can speak\b|\bup\b", low)) and not says_no
        if (tts is True and not says_yes) or (tts is not True and not says_no):
            notes.append("voice answer replaced from SELF")
            visible = voice_line(tts)
    return {"visible": visible.strip(), "spoken": spoken, "notes": notes}


def proposals(visible: str) -> list[tuple[str, dict]]:
    out = []
    for m in re.finditer(r"/job\s+(on|off)\s+(\d+)", visible or ""):
        out.append(("job.resume" if m.group(1) == "on" else "job.pause", {"id": int(m.group(2))}))
    for m in re.finditer(r"/approve\s+(\d+)", visible or ""):
        out.append(("url.approve", {"id": int(m.group(1))}))
    return out


def _post(body: dict, timeout: float):
    req = urllib.request.Request(HOST + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req, timeout=timeout)


def ask(text: str, *, model: str | None = None, on_token=None, cancel: threading.Event | None = None,
        stream: bool = True, timeout: float = 180, propose: bool = False, probes_override: dict | None = None,
        use_lock: bool = True) -> dict:
    from nova import gpulock
    cfg = dict(DEFAULTS)
    model = model or cfg["model"]
    p = probes_override if probes_override is not None else probes()
    sys_p, _hits = system_prompt(text, cfg["mask"])
    body = {"model": model, "stream": stream, "think": cfg["think"], "keep_alive": cfg["keep_alive"],
            "options": {"num_ctx": cfg["num_ctx"], "temperature": cfg["temperature"],
                        **({"seed": cfg["seed"]} if cfg.get("seed") is not None else {})},
            "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": text}]}
    res = {"model": model, "cancelled": False, "contention": gpulock.foreign_heavy(model)}
    lock = gpulock.acquire("chat", "heavy", ttl_s=timeout + 30, model=model) if use_lock else {"ok": True}
    if not lock.get("ok"):
        return {**res, "visible": f"GPU busy ({lock.get('held_by')}); try again shortly.", "spoken": [], "notes": ["gpu_busy"]}
    raw = ""
    try:
        with _post(body, timeout) as r:
            if not stream:
                raw = (json.loads(r.read().decode()).get("message") or {}).get("content") or ""
            else:
                for line in r:
                    if cancel is not None and cancel.is_set():
                        res["cancelled"] = True
                        break
                    if not line.strip():
                        continue
                    ev = json.loads(line.decode())
                    tok = (ev.get("message") or {}).get("content") or ""
                    if tok:
                        raw += tok
                        if on_token:
                            on_token(tok)
                    if ev.get("done"):
                        break
    except Exception as exc:
        return {**res, "visible": f"[ollama] {exc}", "spoken": [], "notes": ["error"], "raw": raw}
    finally:
        if use_lock and lock.get("lock"):
            gpulock.release("chat")
    g = guard(text, raw, p)
    out = {**res, **g, "raw": raw, "system_prompt": sys_p}
    if propose and not res["cancelled"]:
        from nova import cmdinbox
        out["proposed"] = [cmdinbox.propose(v, a, source="chat", why=f"chat: {text[:80]}") for v, a in proposals(g["visible"])]
    return out


def unload(model: str | None = None) -> None:
    body = json.dumps({"model": model or DEFAULTS["model"], "keep_alive": 0}).encode()
    req = urllib.request.Request(HOST + "/api/generate", data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        pass
