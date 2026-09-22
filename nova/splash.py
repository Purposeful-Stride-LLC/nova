"""15s company boot. Shared by TUI and GUI. No extra deps."""

from __future__ import annotations

import sys
import time
import wave
from pathlib import Path

FRAMES = [
    r"""
          .
         * *
        *   *
         * *
          .
    PURPOSEFUL STRIDES
""",
    r"""
         \ | /
        -- * --
         / | \
    PURPOSEFUL STRIDES LLC
         homestead
""",
    r"""
        *     *
           *
        *     *
       N O V A
    instrument of the house
""",
    r"""
      .  *  .  *  .
         ( @ )
      .  *  .  *  .
    xAI / Grok  —  metal face
    Purposeful Strides  —  steward
""",
    r"""
      [=======]  aqueduct
      [=======]
         ||
        NOVA 1.7
    offline. private. standing by.
""",
]


def beep_wav(dest: Path, freq: int = 440, ms: int = 180, rate: int = 22050) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = int(rate * ms / 1000)
    with wave.open(str(dest), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for i in range(n):
            import math

            v = int(8000 * math.sin(2 * math.pi * freq * i / rate))
            w.writeframes(v.to_bytes(2, "little", signed=True))
    return dest


def play_beep(path: Path) -> None:
    try:
        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass


def run(seconds: float = 15.0, sound: bool = True) -> None:
    root = Path(__file__).resolve().parent.parent
    wav = root / "ascii" / "boot.wav"
    if sound:
        try:
            beep_wav(wav, 523, 120)
            play_beep(wav)
        except Exception:
            pass
    step = seconds / max(len(FRAMES), 1)
    for fr in FRAMES:
        sys.stdout.write("\033[H\033[J")
        sys.stdout.write(fr)
        sys.stdout.flush()
        time.sleep(step)
    print()
