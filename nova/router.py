from __future__ import annotations

import re

import json

from nova import db, ollama_talk

TINY = ("nova-sentinel", "qwen2:0.5b", "gemma2:2b")
REASON = ("llama3-groq-tool-use:8b", "qwen3.5:9b", "qwen3:8b", "llama3:8b", "nova-commander")
YESNO = re.compile(r"^\s*(is|are|can|does|do|will|should|yes\s+or\s+no)\b", re.I)


def catalog() -> list[str]:
    rows = ollama_talk.tags_full() if hasattr(ollama_talk, "tags_full") else []
    names = ollama_talk.tags()
    for m in rows:
        name = m.get("name") or ""
        if name:
            db.put_fact("Ax-OLLAMA", name, json.dumps({"name": name, "size": m.get("size")}))
    if names:
        db.put_fact("Ax-OLLAMA", "roster", "\n".join(names))
        try:
            from nova import office

            office.assign_from_roster(names)
        except Exception:
            pass
    return names


def pick(question: str, requested: str | None = None) -> str:
    names = catalog()
    if requested:
        if not names or any(requested == n or requested in n for n in names):
            return requested
    if YESNO.match(question or "") or len((question or "").split()) <= 6:
        for hint in TINY:
            for n in names:
                if hint in n:
                    return n
    for hint in REASON:
        for n in names:
            if hint in n:
                return n
    return requested or ollama_talk.DEFAULT_MODEL
