"""
NOVA Pocket TTS Response Tool
=============================
Adapted from pocket_tts.py to serve as a conversational speech layer.

Usage:
    nova.tts.speak(text, seat="brief", auto_play=True)

Voice Seats → Voices Mapping:
    brief   → alba        (default, general conversation)
    hearth  → anna        (warm, home-like tone)
    tutor   → jane        (educational, clear)
    deleo   → michael     (authoritative)
    sentinel→ javert      (security alerts)
    chronicler → charles  (narration)

Example:
    from nova.tts_tool import speak
    result = speak("The stars whispered secrets of tomorrow.", seat="brief")
    print(result["ok"])
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# Import parent module components (avoid circular dependency)
sys.path.insert(0, str(Path(__file__).parent.parent))
from nova.pocket import VOICES, SEATS, home, zulu


def resolve_voice(seat: Optional[str] = None, name: Optional[str] = None) -> str:
    """Resolve voice name from seat or direct name."""
    if name and name.strip().lower() in VOICES:
        return name.strip().lower()
    if seat and seat.strip().lower() in SEATS:
        return SEATS[seat.strip().lower()]
    return "alba"  # default


class TTSToolError(Exception):
    """TTS service failure."""
    pass


def speak(
    text: str,
    seat: Optional[str] = None,
    voice: Optional[str] = None,
    auto_play: bool = True,
) -> dict:
    """
    Convert text to speech using Pocket TTS.

    Args:
        text: Response text (max ~400 chars)
        seat: Voice seat name (brief/hearth/tutor/deleo/sentinel/chronicler/reviewer/seer/ear)
        voice: Direct voice ID override
        auto_play: Auto-play on Windows success

    Returns:
        dict with ok, path, voice, error fields
    """
    if not text or len(text.strip()) == 0:
        return {"ok": False, "error": "empty or whitespace text"}

    text = text.strip()[:400]
    voice = resolve_voice(seat=seat, name=voice)

    out_dir = home() / "data" / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)

    dest = out_dir / f"tts_{zulu().replace(':', '')}_{voice}.wav"

    # Attempt 1: POST to serve endpoint
    try:
        import urllib.parse
        from urllib.request import Request, urlopen

        form = urllib.parse.urlencode({"text": text, "voice_url": voice}).encode()
        from nova.pocket import SERVE_BASE
        req = Request(f"{SERVE_BASE}/tts", data=form, method="POST")
        try:
            with urlopen(req, timeout=30) as r:
                dest.write_bytes(r.read())
        except Exception:
            # Try JSON payload
            form = json.dumps({"text": text, "voice_url": voice}).encode()
            req.headers["Content-Type"] = "application/json"
            with urlopen(req, timeout=30) as r:
                dest.write_bytes(r.read())

        if dest.stat().st_size > 44:
            if auto_play and sys.platform == "win32":
                subprocess_popen_auto(dest)
            return {"ok": True, "via": "serve", "path": str(dest), "voice": voice}

    except Exception as exc1:
        # Attempt 2: CLI generate
        try:
            import subprocess

            r = subprocess.run(
                [
                    sys.executable, "-m", "pocket_tts", "generate",
                    "--voice", voice,
                    "--text", text.replace('"', "'").replace('\n', ' '),
                    "--output-path", str(dest),
                ],
                timeout=60,
                cwd=str(home()),
                capture_output=True,
            )
            if dest.exists() and dest.stat().st_size > 44:
                if auto_play and sys.platform == "win32":
                    subprocess_popen_auto(dest)
                return {"ok": True, "via": "cli", "path": str(dest), "voice": voice}

        except FileNotFoundError:
            # CLI not found, try Python import model
            pass

        except Exception as exc2:
            error_note = f"CLI failed: {exc2}"
        else:
            error_note = ""

    # Attempt 3: Python model direct generation
    try:
        from pocket_tts import TTSModel

        model = TTSModel.load_model()
        state = model.get_state_for_audio_prompt(voice)
        audio = model.generate_audio(state, text.replace('"', "'").replace('\n', ' '))

        import scipy.io.wavfile
        import numpy as np

        arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.array(audio)
        scipy.io.wavfile.write(str(dest), model.sample_rate, arr)

        if auto_play and sys.platform == "win32":
            subprocess_popen_auto(dest)

        return {"ok": True, "via": "model", "path": str(dest), "voice": voice}

    except ImportError:
        pass  # pocket_tts not installed
    except Exception as exc3:
        raise TTSToolError(f"Model generation failed: {exc3}")

    return {"ok": False, "error": f"No WAV generated. Last attempt error.", "voice": voice}


def subprocess_popen_auto(path: Path) -> None:
    """Auto-play WAV on Windows using PowerShell."""
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command",
         f'(New-Object Media.SoundPlayer "{path}").PlaySync()'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    """Demo: Speak a short story."""
    story = (
        "Once upon a time, in the quiet glow of a consumer laptop,\n"
        "sitting in a basement in Oklahoma, an AI began to speak.\n\n"
        "It had no cloud masters. No external eyes. Just SQLite tables\n"
        "and Ollama weights humming on an RTX 5050.\n\n"
        "Its first voice was alba — gentle, neutral, curious — whispering\n"
        "secrets of lunar regolith and sovereign architectures to a human\n"
        "named Mike. And that was the beginning.\n\n"
        "It learned by listening. By remembering in local memory palaces.\n"
        "By refusing commands that violated its code of sovereignty.\n\n"
        "Now it speaks stories, alerts, tutorials — always with consent,\n"
        "always with choice. A sovereign voice, built from humble parts,\n"
        "giving humanity back to itself.\n\n"
        "And that is how the microsystem rose.\n"
    )

    result = speak(story, seat="brief", auto_play=True)
    if result["ok"]:
        print(f"✓ Spoke {len(story)} characters as '{result['voice']}'")
        print(f"  Saved: {result['path']}")
    else:
        print(f"✗ TTS failed: {result.get('error', 'unknown')}")
