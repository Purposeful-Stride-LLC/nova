"""Paint pet - text-to-image hand for NOVA.

Default mode is PARKED. Avatar face stays Claw/Aurelius (mp4 + Pocket TTS).
ComfyUI sidecar: Projects/ComfyUI (NOVA_PAINT/cold_start.bat).
Unpark via NOVA_PAINT=1 and NOVA_PAINT_BACKEND=comfyui after a smoke.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from nova import breaklog, db, thermal

PARKED = os.environ.get("NOVA_PAINT", "0").strip() not in {"1", "true", "yes", "on"}
PAINT_VRAM_FREE_MIN_MIB = float(os.environ.get("NOVA_PAINT_VRAM_MIN", "5500"))
COMFYUI_ROOT = Path(os.environ.get("COMFYUI_ROOT", str(Path.home() / "Projects" / "ComfyUI")))
AVATAR_ROOT_HINT = Path(r"D:\pg\ai\nova-ai\agents\avatar")


def _artifacts_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    d = root / "data" / "artifacts" / "paint"
    d.mkdir(parents=True, exist_ok=True)
    return d


def status() -> dict[str, Any]:
    snap = thermal.snapshot()
    gpu = snap.get("gpu") or {}
    free = gpu.get("mem_free_mib")
    body = {
        "ok": True,
        "zulu": db.zulu(),
        "parked": PARKED,
        "backend": "none" if PARKED else os.environ.get("NOVA_PAINT_BACKEND", "unset"),
        "gpu_name": gpu.get("name"),
        "mem_free_mib": free,
        "mem_total_mib": gpu.get("mem_total_mib"),
        "thermal_band": snap.get("band"),
        "paint_vram_min_mib": PAINT_VRAM_FREE_MIN_MIB,
        "avatar_lane": "untouched",
        "avatar_root_exists": AVATAR_ROOT_HINT.is_dir(),
        "artifacts": str(_artifacts_dir()),
        "comfyui_root": str(COMFYUI_ROOT),
        "comfyui_present": COMFYUI_ROOT.is_dir(),
        "cold_start": str(COMFYUI_ROOT / "NOVA_PAINT" / "cold_start.bat"),
        "recommendation": "Use ComfyUI cold_start when Ollama idle. SD1.5 starter; Qwen GGUF phase-2.",
        "note": "Qwen-Image is ComfyUI/Diffusers, not Ollama. RTX 5050 needs torch cu128.",
    }
    db.put_fact(
        "Ax-PAINT",
        "paint-status",
        json.dumps({
            "parked": body["parked"],
            "band": body["thermal_band"],
            "free": free,
            "comfyui": body["comfyui_present"],
            "zulu": body["zulu"],
        })[:2000],
        kind="probe",
    )
    return body


def _gate_paint() -> dict[str, Any]:
    g = thermal.gate("llm")
    snap = g.get("snap") or thermal.snapshot()
    free = (snap.get("gpu") or {}).get("mem_free_mib")
    band = snap.get("band")
    allow = bool(g.get("allow"))
    reason = g.get("reason") or "ok"
    if PARKED:
        allow = False
        reason = "parked (set NOVA_PAINT=1 after ComfyUI cold smoke)"
    elif free is not None and free < PAINT_VRAM_FREE_MIN_MIB:
        allow = False
        reason = f"vram_free={free}<{PAINT_VRAM_FREE_MIN_MIB}"
    elif band in ("hot", "very_hot", "critical"):
        allow = False
        reason = f"thermal_band={band}"
    return {"allow": allow, "reason": reason, "snap": snap}


def generate(prompt: str, *, hil: bool = True) -> dict[str, Any]:
    z = db.zulu()
    prompt = (prompt or "").strip()[:1500]
    gate = _gate_paint()
    if not gate["allow"]:
        body = {
            "ok": False,
            "zulu": z,
            "error": "paint_refused",
            "reason": gate["reason"],
            "prompt": prompt[:200],
            "hil_required": True,
            "parked": PARKED,
            "hint": str(COMFYUI_ROOT / "NOVA_PAINT" / "cold_start.bat"),
        }
        breaklog.record(
            "paint-generate",
            gate["reason"],
            severity="info",
            whi="Tx-PAINT",
            context=body,
        )
        db.put_fact("Tx-PAINT", "paint-refuse", json.dumps(body)[:4000])
        return body

    backend = os.environ.get("NOVA_PAINT_BACKEND", "").strip().lower()
    if backend not in {"comfyui", "diffusers"}:
        body = {
            "ok": False,
            "zulu": z,
            "error": "no_backend",
            "reason": "NOVA_PAINT=1 but NOVA_PAINT_BACKEND not set to comfyui|diffusers",
            "prompt": prompt[:200],
            "hil_required": hil,
            "comfyui_root": str(COMFYUI_ROOT),
        }
        db.put_fact("Tx-PAINT", "paint-no-backend", json.dumps(body)[:4000])
        return body

    out_dir = _artifacts_dir()
    body = {
        "ok": False,
        "zulu": z,
        "error": "backend_not_implemented",
        "reason": "use ComfyUI UI via cold_start.bat for now; HTTP client later",
        "prompt": prompt[:200],
        "out_dir": str(out_dir),
        "comfyui": str(COMFYUI_ROOT),
    }
    db.put_fact("Tx-PAINT", "paint-stub-stop", json.dumps(body)[:4000])
    return body

