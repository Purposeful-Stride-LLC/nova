"""Probes. Inline so the kit boots even if sibling files lag."""

from __future__ import annotations

import platform
import socket
from datetime import datetime, timezone


def _z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_probe(name: str) -> dict:
    try:
        return PROBES[name]()
    except KeyError:
        return {"source": name, "ok": False, "error": "no probe"}
    except Exception as exc:
        return {"source": name, "ok": False, "error": str(exc)}


def _hardware():
    row = {"source": "hardware", "ok": True, "zulu": _z(), "system": platform.system(), "node": platform.node()}
    try:
        import psutil

        row["cpu"] = psutil.cpu_count(logical=True)
        row["ram_gb"] = round(psutil.virtual_memory().total / 1024**3, 2)
    except Exception:
        pass
    return row


def _vision():
    row = {"source": "vision", "ok": True, "zulu": _z(), "opencv": False}
    try:
        import cv2

        row["opencv"] = True
        row["cv2"] = cv2.__version__
    except Exception as exc:
        row["note"] = str(exc)
    return row


def _process():
    return {"source": "process", "ok": True, "zulu": _z(), "note": "names only"}


def _network():
    return {
        "source": "network",
        "ok": True,
        "zulu": _z(),
        "hostname": socket.gethostname(),
        "loopback": True,
    }


def _lan():
    return {"source": "lan", "ok": True, "zulu": _z(), "note": "see /spyder"}


def _ai():
    import urllib.request

    ollama_ok = False
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1)
        ollama_ok = True
    except Exception:
        pass
    openclaw_18789 = False
    try:
        s = socket.create_connection(("127.0.0.1", 18789), timeout=1.0)
        s.close()
        openclaw_18789 = True
    except Exception:
        pass
    openclaw_models = False
    try:
        urllib.request.urlopen("http://127.0.0.1:18789/v1/models", timeout=1.5)
        openclaw_models = True
    except Exception:
        pass
    return {
        "source": "ai_runtime",
        "ok": True,
        "zulu": _z(),
        "ollama_loopback": ollama_ok,
        "openclaw_18789": openclaw_18789,
        "openclaw_models": openclaw_models,
    }


def _vol():
    return {"source": "volumes", "ok": True, "zulu": _z()}


PROBES = {
    "hardware": _hardware,
    "vision": _vision,
    "process": _process,
    "network": _network,
    "lan": _lan,
    "ai_runtime": _ai,
    "volumes": _vol,
}
