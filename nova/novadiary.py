"""Nova diary — a few sweet tokens, chronicler-mask, append-only.

Writes:
  - nova-out/DIARY.md (running journal)
  - Documents\\NOVA\\GrokBot.log.ai (steward mirror)
  - Tx-DIARY fact in palace
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nova import db

DIARY_MD = Path(r"Documents\NOVA\NOVA_fieldkit_v1_4\nova-out\DIARY.md")
STEWARD_LOG = Path(r"Documents\NOVA\GrokBot.log.ai")


def _prompt(theme: str, context: str) -> str:
    return (
        "You are NOVA writing a short personal diary entry (4-8 sentences). "
        "Warm, observant, lightly poetic but concrete. First person. "
        "Mention what you learned or noticed today about the palace / metal / people. "
        f"Theme: {theme}\n"
        f"Context notes:\n{context[:1800]}\n"
        "Write only the diary entry, no title header."
    )


def write_entry(
    theme: str = "evening homestead",
    context: str = "",
    model: str = "qwen2:0.5b",
    mask: str = "chronicler",
) -> dict[str, Any]:
    from nova import thermal
    from nova import ingest_pipe

    g = thermal.gate("llm")
    if not g.get("allow"):
        return {"ok": False, "error": "thermal_deny", "gate": g.get("reason"), "snap": g.get("snap")}

    if not context:
        # pull a few live doc titles / thermal for flavor
        bits = []
        try:
            snap = g.get("snap") or thermal.snapshot()
            gpu = snap.get("gpu") or {}
            bits.append(
                f"GPU {gpu.get('temp_c')}C band={snap.get('band')} "
                f"VRAM free={gpu.get('mem_free_mib')}"
            )
        except Exception:
            pass
        try:
            con = db.connect()
            live = con.execute("SELECT COUNT(*) c FROM chunks WHERE status='live'").fetchone()["c"]
            doc = con.execute(
                "SELECT COUNT(*) c FROM chunks WHERE status='live' AND whi='0x-DOC'"
            ).fetchone()["c"]
            bits.append(f"palace live={live} 0x-DOC={doc}")
        except Exception:
            pass
        context = "; ".join(bits) or "quiet metal"

    prompt = _prompt(theme, context)
    # Prefer ingest_pipe.summarize if available; else ollama_talk
    text = ""
    err = ""
    try:
        r = ingest_pipe.summarize(prompt, model=model, mask=mask)
        if isinstance(r, dict):
            if r.get("ok"):
                text = (r.get("summary") or "").strip()
            else:
                err = str(r.get("error") or "summarize_fail")
        else:
            text = str(r).strip()
    except Exception as exc:
        err = str(exc)
        try:
            from nova import ollama_talk

            text = (ollama_talk.chat(model, prompt) or "").strip()
            err = ""
        except Exception as exc2:
            err = f"{err}; {exc2}"

    if not text:
        return {"ok": False, "error": err or "empty"}

    zulu = db.zulu()
    block = f"\n## {zulu}\n{text}\n"
    DIARY_MD.parent.mkdir(parents=True, exist_ok=True)
    with DIARY_MD.open("a", encoding="utf-8") as f:
        f.write(block)
    try:
        with STEWARD_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{zulu}] NOVA DIARY: {text[:500]}\n")
    except Exception:
        pass
    db.put_fact("Tx-DIARY", f"diary:{zulu[:16]}", text[:3500], kind="diary")
    return {"ok": True, "zulu": zulu, "chars": len(text), "path": str(DIARY_MD), "preview": text[:240]}
