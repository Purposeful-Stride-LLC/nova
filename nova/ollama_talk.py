"""Loopback Ollama. Never leave 127.0.0.1."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3-groq-tool-use:8b"


def tags_full() -> list[dict]:
    try:
        with urllib.request.urlopen(f"{HOST}/api/tags", timeout=2) as r:
            data = json.loads(r.read().decode())
        return list(data.get("models") or [])
    except Exception:
        return []


def tags() -> list[str]:
    return [m.get("name", "") for m in tags_full() if m.get("name")]


def live() -> bool:
    try:
        urllib.request.urlopen(f"{HOST}/api/tags", timeout=1)
        return True
    except Exception:
        return False


def chat(model: str, prompt: str, timeout: int = 120) -> str:
    body = json.dumps(
        {
            "model": model or DEFAULT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_ctx": 4096},
        }
    ).encode()
    req = urllib.request.Request(
        f"{HOST}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        return str(data.get("response") or "")
    except urllib.error.URLError as exc:
        return f"[ollama down] {exc}"
