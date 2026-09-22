"""Brain adapter seam — swap only complete().

Adapters:
  ollama.local  — HAVE (loopback generate)
  openai.compat — Ollama OpenAI-compatible /v1 (Qwen path)
  xai.grok      — stub until steward places key in data/secrets (never git)

OpenClaw may be the messenger for outbound channel delivery; this module is
inference only.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from nova import breaklog, ollama_talk


def complete(
    system: str,
    user: str,
    *,
    images: list[str] | None = None,
    model: str | None = None,
    provider: str = "ollama.local",
) -> str:
    _ = images  # reserved for VLM adapters
    provider = (provider or "ollama.local").lower()
    if provider in {"ollama.local", "ollama"}:
        prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
        return ollama_talk.chat(model or ollama_talk.DEFAULT_MODEL, prompt)
    if provider in {"openai.compat", "ollama.openai"}:
        return _openai_compat(system, user, model=model or "llama3-groq-tool-use:8b")
    if provider in {"xai.grok", "grok", "xai"}:
        return _xai_grok(system, user, model=model or "grok-2")
    breaklog.record("brain", f"unknown provider {provider}", severity="error")
    return f"[brain] unknown provider {provider}"


def _openai_compat(system: str, user: str, model: str) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode())
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    except Exception as exc:
        breaklog.record("brain.openai.compat", str(exc), severity="error")
        return f"[brain down] {exc}"


def _xai_grok(system: str, user: str, model: str) -> str:
    _ = (system, user, model)
    secrets = Path(ollama_talk.__file__).resolve().parents[1] / "data" / "secrets" / "xai_api_key.txt"
    if not secrets.is_file():
        msg = "xAI key missing: place key in data/secrets/xai_api_key.txt (never commit)"
        breaklog.record("brain.xai.grok", msg, severity="warn", whi="Tx-BRAIN")
        return f"[brain xai] {msg}"
    key = secrets.read_text(encoding="utf-8").strip()
    if not key:
        return "[brain xai] empty key file"
    breaklog.record(
        "brain.xai.grok",
        "adapter stub — enable HTTP when ready",
        severity="info",
        whi="Ax-BRAIN",
        open_report=False,
    )
    return "[brain xai] stub ready; HTTP not enabled in this cut — use ollama.local"
