"""Nova awareness runtime probes."""

import httpx
import socket
import threading
from datetime import datetime, timezone


def _z():
    """Current UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat().replace(" ", "T")


run_probe = None


class PROBES:
    """Probe registry for ai_runtime."""

    hardware = False
    vision = False
    process = False
    network = False
    lan = False
    ai_runtime = False


def _ai():
    """AI runtime probe suite."""
    ollama_loopback = False
    openclaw_18789 = False
    openclaw_models = False

    try:
        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5)
        ollama_loopback = resp.status_code == 200
    except Exception:
        pass

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", 18789))
        openclaw_18789 = True
    except Exception:
        pass
    finally:
        sock.close()

    try:
        resp = httpx.get("http://127.0.0.1:18789/v1/models", timeout=5)
        openclaw_models = resp.status_code == 200
    except Exception:
        openclaw_models = False

    return {
        "source": "ai_runtime",
        "ok": True,
        "zulu": _z(),
        "ollama_loopback": ollama_loopback,
        "openclaw_18789": openclaw_18789,
        "openclaw_models": openclaw_models,
    }


def hardware_probe():
    """Probe hardware availability."""
    import psutil

    try:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        return {"source": "hardware", "ok": True, "cpu": cpu, "mem": mem}
    except Exception:
        return {"source": "hardware", "ok": False}


def vision_probe():
    """Probe vision subsystem."""
    try:
        from PIL import Image
        pil_ok = True
    except ImportError:
        pil_ok = False
    except Exception:
        pil_ok = False
    return {"source": "vision", "ok": pil_ok}


def process_probe():
    """Probe process table."""
    try:
        psutil.pid_exists(os.getpid())
        return {"source": "process", "ok": True, "pid": os.getpid()}
    except Exception:
        return {"source": "process", "ok": False}


def network_probe():
    """Probe local network stack."""
    try:
        socket.gethostbyname(socket.gethostname())
        return {"source": "network", "ok": True, "hosts": [socket.gethostname()]}
    except Exception:
        return {"source": "network", "ok": False}


def lan_probe():
    """Probe LAN connectivity."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 53))
        return {"source": "lan", "ok": True, "gw": "8.8.8.8"}
    except Exception:
        return {"source": "lan", "ok": False}


def ai_runtime_probe():
    """Probe ai_runtime integration."""
    import psutil
    return _ai()
