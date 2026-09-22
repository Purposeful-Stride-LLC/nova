"""L0 awareness probes — code only, no LLM. Windows-first."""
from __future__ import annotations

from nova.awareness import probes as _probes

PROBES = {
    "hardware": _probes.hardware,
    "process": _probes.process,
    "network": _probes.network,
    "lan": _probes.lan,
    "ai_runtime": _probes.ai_runtime,
    "volumes": _probes.volumes,
    "vision": _probes.vision,
}


def run_probe(name: str) -> dict:
    fn = PROBES.get((name or "").strip().lower())
    if not fn:
        return {"source": name, "ok": False, "error": "unknown probe"}
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"source": name, "ok": False, "error": str(exc)}


def list_probes() -> list[str]:
    return sorted(PROBES.keys())
