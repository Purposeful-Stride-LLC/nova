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
    "aurelius": "michael",
    "scout": "eve",
    "analyst": "anna",
    "skeptic": "javert",
    "synthesist": "charles",
    "grokbot": "anna",
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


def speak_employee(text: str, employee_or_mask: str = "brief") -> dict:
    """Speak as a palace employee / mask using Pocket TTS only."""
    key = (employee_or_mask or "brief").strip().lower()
    if "@" in key:
        key = key.split("@", 1)[0]
    voice = SEATS.get(key) or DEFAULT_VOICE
    return speak(text, voice)

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
                play = _play(dest)
                return {"ok": True, "via": "serve-multipart", "path": str(dest), "voice": voice, "note": note, "play": play}
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
            play = _play(dest)
            return {"ok": True, "via": "cli", "path": str(dest), "voice": voice, "note": note, "play": play}
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
        play = _play(dest)
        return {"ok": True, "via": "import", "path": str(dest), "voice": voice, "play": play}
    except Exception as exc:
        errors.append(f"import {exc}")
        try:
            from nova import breaklog

            breaklog.record("pocket.speak", " | ".join(errors)[:1500], severity="warn", whi="Tx-TTS")
        except Exception:
            pass
        return {"ok": False, "error": " | ".join(errors), "note": note, "voice": voice}



def _normalize_wav(path) -> "Path":
    """Pocket TTS often writes a bogus data-chunk size (~2e9). Rewrite PCM header."""
    from pathlib import Path as P
    import struct
    import wave

    path = P(path)
    data = path.read_bytes()
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return path
    pos = 12
    pcm = None
    ch, rate, width = 1, 24000, 2
    while pos + 8 <= len(data):
        cid = data[pos : pos + 4]
        sz = struct.unpack_from("<I", data, pos + 4)[0]
        body = data[pos + 8 : pos + 8 + max(0, min(sz, len(data) - (pos + 8)))]
        if cid == b"fmt " and len(body) >= 16:
            _af, ch, rate, _br, _ba, bits = struct.unpack_from("<HHIIHH", body[:16])
            width = max(1, bits // 8)
        if cid == b"data":
            # Trust file remainder when claimed size is absurd
            if sz > len(data) or sz > 50_000_000:
                pcm = data[pos + 8 :]
            else:
                pcm = body
            break
        pos += 8 + sz
        if sz % 2:
            pos += 1
    if not pcm:
        return path
    fixed = path.with_name(path.stem + "_play.wav")
    with wave.open(str(fixed), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return fixed


def _play(path) -> dict:
    """Play wav on Windows. Returns {ok, via, path, error?}. Never swallow failures."""
    from pathlib import Path as P

    path = P(path)
    if not path.exists():
        return {"ok": False, "error": "missing wav", "path": str(path)}
    play_path = _normalize_wav(path)
    errors: list[str] = []
    if sys.platform == "win32":
        try:
            import winsound

            winsound.PlaySound(str(play_path.resolve()), winsound.SND_FILENAME | winsound.SND_NODEFAULT)
            return {"ok": True, "via": "winsound", "path": str(play_path)}
        except Exception as exc:
            errors.append(f"winsound {exc}")
        # fallback: SoundPlayer on normalized file
        try:
            pp = str(play_path.resolve()).replace("'", "''")
            ps = "(New-Object Media.SoundPlayer '" + pp + "').PlaySync()"
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode == 0:
                return {"ok": True, "via": "SoundPlayer", "path": str(play_path)}
            errors.append(f"SoundPlayer rc={r.returncode} {(r.stderr or '')[:200]}")
        except Exception as exc:
            errors.append(f"SoundPlayer {exc}")
        try:
            subprocess.Popen(["cmd", "/c", "start", "", str(play_path.resolve())], shell=False)
            return {"ok": True, "via": "start", "path": str(play_path), "note": "default app"}
        except Exception as exc:
            errors.append(f"start {exc}")
    return {"ok": False, "error": "; ".join(errors) or "no play method", "path": str(play_path)}

