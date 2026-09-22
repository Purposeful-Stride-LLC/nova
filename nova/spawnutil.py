"""One spawn door. Track PIDs. Never use unquoted `start TITLE`."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from nova.db import home, zulu

CREATE_NEW_CONSOLE = 0x00000010
REGISTRY = None  # set in _path()


def _path() -> Path:
    p = home() / "data" / "artifacts" / "spawns.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load() -> list[dict]:
    p = _path()
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(rows: list[dict]) -> None:
    _path().write_text(json.dumps(rows[-40:], indent=2), encoding="utf-8")


def alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            SYNCHRONIZE = 0x00100000
            h = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
            if h:
                ctypes.windll.kernel32.CloseHandle(h)
                return True
        except Exception:
            pass
        # tasklist fallback
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return str(pid) in (r.stdout or "")
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def spawn(args: list[str], name: str, cwd: Path | None = None) -> dict:
    """Start a child. Return {name, pid, cmd, zulu, alive}."""
    cwd = cwd or home()
    kw: dict = {"cwd": str(cwd)}
    if sys.platform == "win32":
        kw["creationflags"] = CREATE_NEW_CONSOLE
    proc = subprocess.Popen(args, **kw)
    rec = {
        "name": name,
        "pid": int(proc.pid),
        "cmd": args,
        "zulu": zulu(),
        "alive": True,
    }
    rows = [r for r in _load() if r.get("name") != name] + [rec]
    _save(rows)
    print(f"spawn {name} pid={proc.pid} {args}")
    return rec



def spawn_titled(title: str, args: list[str], name: str, cwd: Path | None = None) -> dict:
    """Windows: open a visible console with an exact window title via start "TITLE" cmd /k.
    TITLE must be quoted — unquoted start treats the first token as the executable.
    Non-Windows falls back to spawn() (CREATE_NEW_CONSOLE / new terminal).
    """
    cwd = cwd or home()
    if sys.platform != "win32":
        return spawn(args, name=name, cwd=cwd)
    # Build: start "TITLE" cmd /k "cd /d CWD && set PYTHONPATH=CWD && arg0 arg1 ..."
    title = (title or name or "NOVA").replace('"', "")
    parts = []
    for a in args:
        a = str(a)
        if " " in a or any(c in a for c in '&<>|^'):
            parts.append('"' + a.replace('"', '') + '"')
        else:
            parts.append(a)
    inner = " ".join(parts)
    cwd_s = str(cwd)
    # Keep PYTHONPATH so -m nova.* finds the kit
    chain = f'cd /d "{cwd_s}" && set PYTHONPATH={cwd_s}&& {inner}'
    cmdline = f'start "{title}" cmd /k "{chain}"'
    proc = subprocess.Popen(cmdline, shell=True, cwd=cwd_s)
    rec = {
        "name": name,
        "pid": int(proc.pid),
        "cmd": args,
        "title": title,
        "zulu": zulu(),
        "alive": True,
        "mode": "start_titled",
    }
    rows = [r for r in _load() if r.get("name") != name] + [rec]
    _save(rows)
    print(f"spawn_titled {name!r} title={title!r} {args}")
    return rec

def list_spawns() -> list[dict]:
    rows = _load()
    for r in rows:
        r["alive"] = alive(int(r.get("pid") or 0))
    _save(rows)
    return rows
