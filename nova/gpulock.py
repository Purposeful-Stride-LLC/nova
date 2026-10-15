"""GPU exclusivity for NOVA 2.1: at most ONE heavy model job at a time.

Classes: none (no model), light (qwen2:0.5b-class, <1 GB), vision (moondream, ~1.7 GB), heavy
(8B-class reasoners, coder, diary/chat). Only 'heavy' and 'vision' take the lock; 'light' and
'none' never wait. The lock is a JSON file under <NOVA_HOME>/data/run/ so the daemon, the GUI chat
worker and the TUI share it. A stale lock (dead pid or past 'until') is ignored.
Also reports a FOREIGN heavy model resident in Ollama (e.g. another install's qwen3.5:9b) so callers
can defer instead of evicting it.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

EXCLUSIVE = {"heavy", "vision"}
HEAVY_BYTES = 3_000_000_000  # resident model >= 3 GB counts as heavy


def _path() -> Path:
    from nova import db
    d = db.home() / "data" / "run"
    d.mkdir(parents=True, exist_ok=True)
    return d / "gpu.lock"


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        if os.name == "nt":
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
            if not h:
                return False
            code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
            ctypes.windll.kernel32.CloseHandle(h)
            return code.value == 259  # STILL_ACTIVE
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def holder() -> dict | None:
    p = _path()
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if time.time() > float(rec.get("until") or 0) or not _alive(int(rec.get("pid") or 0)):
        return None
    return rec


def acquire(who: str, cls: str = "heavy", ttl_s: float = 900, model: str = "") -> dict:
    if cls not in EXCLUSIVE:
        return {"ok": True, "lock": False, "cls": cls}
    cur = holder()
    if cur and cur.get("who") != who:
        return {"ok": False, "busy": True, "held_by": cur.get("who"), "model": cur.get("model")}
    rec = {"who": who, "cls": cls, "pid": os.getpid(), "since": time.time(), "until": time.time() + ttl_s, "model": model}
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(rec), encoding="utf-8")
    os.replace(tmp, _path())
    return {"ok": True, "lock": True, **rec}


def release(who: str) -> None:
    cur = holder()
    if cur and cur.get("who") == who:
        cur["until"] = 0  # release by expiry; the lock file is reused, never deleted
        tmp = _path().with_suffix(".tmp")
        tmp.write_text(json.dumps(cur), encoding="utf-8")
        os.replace(tmp, _path())


@contextmanager
def exclusive(who: str, cls: str = "heavy", ttl_s: float = 900, model: str = ""):
    r = acquire(who, cls, ttl_s, model)
    try:
        yield r
    finally:
        if r.get("lock"):
            release(who)


def ollama_resident(timeout: float = 1.5) -> list[dict] | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=timeout) as r:
            data = json.loads(r.read().decode())
        return [{"name": m.get("name"), "size": int(m.get("size") or 0),
                 "size_vram": int(m.get("size_vram") or 0)} for m in data.get("models") or []]
    except Exception:
        return None


def foreign_heavy(want_model: str) -> list[dict]:
    """Heavy models resident in Ollama that are not the one we want (loading ours would evict them)."""
    res = ollama_resident() or []
    return [m for m in res if m["name"] != want_model and m["size"] >= HEAVY_BYTES]
