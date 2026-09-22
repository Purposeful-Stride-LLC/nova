"""Boot order: pocket-tts serve (if down) → daemon → GUI.
TUI is never auto. python -m nova.tui only.

Windows: do NOT use `start TITLE cmd` without quoting TITLE.
Unquoted start treats the title as the executable (NOVA-gui / NOV-gui).
Use spawnutil.spawn_titled so TTS and daemon consoles are visible and named.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

CREATE_NEW_CONSOLE = 0x00000010


def kit_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _serve_up() -> bool:
    from nova.pocket import SERVE_BASE

    for url in (f"{SERVE_BASE}/health", SERVE_BASE):
        try:
            urllib.request.urlopen(url, timeout=0.4)
            return True
        except Exception:
            continue
    return False


def _spawn_gui():
    """GUI is a Qt window; CREATE_NEW_CONSOLE is fine (own process, visible)."""
    from nova.spawnutil import spawn

    return spawn([sys.executable, "-m", "nova.gui"], name="nova.gui", cwd=kit_root())


def main() -> None:
    from nova import splash
    from nova.pocket import SERVE_PORT
    from nova.spawnutil import spawn_titled

    root = kit_root()
    fast = os.environ.get("NOVA_FAST", "").strip() in {"1", "true", "yes"}
    splash.run(1.5 if fast else 8.0, sound=not fast)

    if not _serve_up():
        print("starting pocket_tts serve (titled console)")
        spawn_titled(
            "NOVA Pocket TTS :8000",
            [sys.executable, "-m", "pocket_tts", "serve", "--port", str(SERVE_PORT)],
            name="pocket_tts",
            cwd=root,
        )
        time.sleep(1.5)
    else:
        print("pocket_tts already up on :8000")

    print("starting daemon (titled console)")
    spawn_titled(
        "NOVA daemon",
        [sys.executable, "-m", "nova"],
        name="nova",
        cwd=root,
    )
    time.sleep(0.8)

    print("starting gui")
    _spawn_gui()
    print("TUI is manual:  python -m nova.tui")
    print("If GUI exits:     pip install PySide6")


if __name__ == "__main__":
    main()
