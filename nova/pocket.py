"""Pocket TTS hook. Optional. CPU. Voices mapped to Deleo seats.

Serve contract (Kyutai Pocket TTS OpenAPI):
  POST http://127.0.0.1:8000/tts  (listen port 8000 - NOT 3000; 3000 is only Kyutai CORS demo origin)
  Content-Type: multipart/form-data
  fields: text (required), voice_url (optional built-in name e.g. anna)
  response: audio/wav bytes
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from nova.db import home, zulu

# Canonical serve - always 8000 per Pocket TTS manual / OpenAPI. Never 3000.
SERVE_HOST = "127.0.0.1"
SERVE_PORT = 8000
SERVE_BASE = f"http://{SERVE_HOST}:{SERVE_PORT}"
DEFAULT_VOICE = "anna"

VOICES = (
    "alba",
    "anna",
    "azelma",
    "bill_boerst",
    "caro_davy",
    "charles",
    "cosette",
    "eponine",
    "eve",
    "fantine",
    "george",
    "jane",
    "jean",
    "javert",
    "marius",
    "mary",
    "michael",
    "paul",
    "peter_yearsley",
    "stuart_bell",
    "vera",
    "giovanni",
    "lola",
    "juergen",
    "rafael",
    "estelle",
)

SEATS = {
    "brief": "anna",
    "hearth": "anna",
    "tutor": "jane",
    "deleo": "michael",
    "sentinel": "javert",
    "chronicler": "charles",
    "reviewer": "george",
    "seer": "anna",
    "ear": "javert",
    "openclaw": "michael",
    "qwen": "george",
    "clerk": "anna",
}

_model = None
_states: dict[str, object] = {}


def serve_up() -> bool:
    import urllib.request

    for url in (f"{SERVE_BASE}/health", SERVE_BASE):
        try:
            urllib.request.urlopen(url, timeout=0.6)
            return True
        except Exception:
            continue
    return False


def installed() -> bool:
    if serve_up():
        return True
    try:
        import pocket_tts  # noqa: F401

        return True
    except ImportError:
        return shutil.which("pocket-tts") is not None


def ensure_serve() -> str:
    import time

    if serve_up():
        return "up"
    try:
        from nova.spawnutil import spawn

        spawn(
            [sys.executable, "-m", "pocket_tts", "serve", "--port", str(SERVE_PORT)],
            name="pocket_tts",
            cwd=home(),
        )
    except Exception as exc:
        return f"spawn {exc}"
    for _ in range(20):
        time.sleep(0.4)
        if serve_up():
            return "started"
    return "warming"


def pip_hint() -> str:
    return "pip install pocket-tts   # Windows wheels are CPU-only by default"


def _load():
    global _model
    if _model is not None:
        return _model
    from pocket_tts import TTSModel

    _model = TTSModel.load_model()
    return _model


def resolve_voice(name: str) -> str:
    n = (name or "anna").strip().lower()
    if n in SEATS:
        return SEATS[n]
    if n in VOICES:
        return n
    return "anna"


def _state(voice: str):
    voice = resolve_voice(voice)
    if voice not in _states:
        model = _load()
        _states[voice] = model.get_state_for_audio_prompt(voice)
    return _states[voice]


def _multipart(fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = "----NovaPocketTTS7MA4YWxk"
    lines: list[str] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}")
        lines.append(f'Content-Disposition: form-data; name="{name}"')
        lines.append("")
        lines.append(str(value))
    lines.append(f"--{boundary}--")
    lines.append("")
    body = "\r\n".join(lines).encode("utf-8")
    ctype = f"multipart/form-data; boundary={boundary}"
    return body, ctype


def start_serve_window() -> dict:
    """Open pocket_tts serve in a titled parallel console on :8000. Does not touch the NOVA daemon."""
    if serve_up():
        return {"ok": True, "already": True, "base": SERVE_BASE}
    try:
        from nova.spawnutil import spawn_titled

        rec = spawn_titled(
            "NOVA Pocket TTS :8000",
            [sys.executable, "-m", "pocket_tts", "serve", "--port", str(SERVE_PORT)],
            name="pocket_tts",
            cwd=home(),
        )
        return {
            "ok": True,
            "spawned": True,
            "pid": rec.get("pid"),
            "title": rec.get("title"),
            "base": SERVE_BASE,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "base": SERVE_BASE}


def speak(text: str, voice: str = "anna") -> dict:
    """Multipart /tts first (correct OpenAPI). CLI generate next. Import last."""
    import urllib.request

    text = (text or "").strip()[:400]
    if not text:
        return {"ok": False, "error": "empty text"}
    voice = resolve_voice(voice)
    out_dir = home() / "data" / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"tts_{zulu().replace(':', '')}_{voice}.wav"
    note = ensure_serve()
    errors: list[str] = []
    if serve_up():
        body, ctype = _multipart({"text": text, "voice_url": voice})
        try:
            req = urllib.request.Request(
                f"{SERVE_BASE}/tts",
                data=body,
                headers={"Content-Type": ctype},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            if raw[:4] == b"RIFF" or len(raw) > 44:
                dest.write_bytes(raw)
                _play(dest)
                return {"ok": True, "via": "serve-multipart", "path": str(dest), "voice": voice, "note": note}
            errors.append(f"serve non-wav bytes={len(raw)} head={raw[:24]!r}")
        except Exception as exc:
            errors.append(f"serve {exc}")
    try:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pocket_tts",
                "generate",
                "--voice",
                voice,
                "--text",
                text,
                "--output-path",
                str(dest),
            ],
            timeout=90,
            cwd=str(home()),
            capture_output=True,
            text=True,
        )
        if dest.exists() and dest.stat().st_size > 44:
            _play(dest)
            return {"ok": True, "via": "cli", "path": str(dest), "voice": voice, "note": note}
        errors.append(f"cli rc={r.returncode} {(r.stderr or r.stdout or '')[:200]}")
    except Exception as exc:
        errors.append(f"cli {exc}")
    try:
        import scipy.io.wavfile
        from numpy import asarray

        model = _load()
        audio = model.generate_audio(_state(voice), text)
        arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else asarray(audio)
        scipy.io.wavfile.write(str(dest), model.sample_rate, arr)
        _play(dest)
        return {"ok": True, "via": "import", "path": str(dest), "voice": voice}
    except Exception as exc:
        errors.append(f"import {exc}")
        try:
            from nova import breaklog

            breaklog.record("pocket.speak", " | ".join(errors)[:1500], severity="warn", whi="Tx-TTS")
        except Exception:
            pass
        return {"ok": False, "error": " | ".join(errors), "note": note, "voice": voice}


def _play(path) -> None:
    from pathlib import Path as P

    path = P(path)
    if sys.platform == "win32":
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f'(New-Object Media.SoundPlayer "{path}").PlaySync()',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
