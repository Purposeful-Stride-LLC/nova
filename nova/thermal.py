"""L0 thermal + VRAM gate for shared NVIDIA metal. No LLM."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any

from nova import db

# Soft bands (laptop GPU). Prefer staying under WARM for sustained work.
COOL_MAX = 65
WARM_MAX = 75
HOT_MAX = 82
CRIT = 88
VRAM_FREE_MIN_MIB = 1200


def _nvidia() -> dict[str, Any]:
    if not shutil.which("nvidia-smi"):
        return {"ok": False, "error": "no nvidia-smi"}
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=8,
        ).strip()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    line = out.splitlines()[0] if out else ""
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 6:
        return {"ok": False, "error": "parse", "raw": line}

    def num(s: str) -> float | None:
        try:
            return float(re.sub(r"[^0-9.]+", "", s) or "nan")
        except Exception:
            return None

    used, total = num(parts[3]), num(parts[4])
    free = (total - used) if used is not None and total is not None else None
    return {
        "ok": True,
        "name": parts[0],
        "temp_c": num(parts[1]),
        "util_pct": num(parts[2]),
        "mem_used_mib": used,
        "mem_total_mib": total,
        "mem_free_mib": free,
        "power_w": num(parts[5]),
    }


def _cpu_thermal_c() -> float | None:
    """Best-effort Windows thermal zone (Kelvin or tenths-Kelvin)."""
    try:
        ps = (
            "Get-CimInstance Win32_PerfFormattedData_Counters_ThermalZoneInformation "
            "| Select-Object -ExpandProperty Temperature"
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps], text=True, timeout=8
        ).strip()
        vals = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                v = float(line)
            except ValueError:
                continue
            # Heuristic: >200 likely Kelvin; >1000 tenths-Kelvin
            if v > 1000:
                vals.append(v / 10.0 - 273.15)
            elif v > 200:
                vals.append(v - 273.15)
            else:
                vals.append(v)
        return max(vals) if vals else None
    except Exception:
        return None


def snapshot() -> dict[str, Any]:
    gpu = _nvidia()
    cpu_c = _cpu_thermal_c()
    temp = gpu.get("temp_c") if gpu.get("ok") else None
    band = "unknown"
    if temp is not None:
        if temp < COOL_MAX:
            band = "cool"
        elif temp < WARM_MAX:
            band = "warm"
        elif temp < HOT_MAX:
            band = "hot"
        elif temp < CRIT:
            band = "very_hot"
        else:
            band = "critical"
    free = gpu.get("mem_free_mib") if gpu.get("ok") else None
    vram_ok = free is None or free >= VRAM_FREE_MIN_MIB
    llm_ok = band in ("cool", "warm", "unknown") and vram_ok and band != "critical"
    if band in ("hot", "very_hot", "critical"):
        llm_ok = False
    out = {
        "ok": True,
        "zulu": db.zulu(),
        "gpu": gpu,
        "cpu_temp_c": cpu_c,
        "band": band,
        "vram_ok": vram_ok,
        "llm_ok": llm_ok,
        "limits": {
            "cool_max": COOL_MAX,
            "warm_max": WARM_MAX,
            "hot_max": HOT_MAX,
            "crit": CRIT,
            "vram_free_min_mib": VRAM_FREE_MIN_MIB,
        },
    }
    return out


def gate(kind: str = "llm") -> dict[str, Any]:
    """Return allow/deny for workload kind: llm|l0|speak."""
    snap = snapshot()
    band = snap.get("band")
    allow = True
    reason = "ok"
    if kind == "llm":
        allow = bool(snap.get("llm_ok"))
        if not allow:
            reason = f"thermal_band={band} vram_ok={snap.get('vram_ok')}"
            try:
                from nova import office

                if band in ("very_hot", "critical"):
                    office.report(2, "thermal gate deny", json.dumps(snap)[:1500])
                elif band == "hot":
                    office.report(1, "thermal warm-hold", json.dumps({
                        "band": band, "gpu": snap.get("gpu")
                    })[:800])
            except Exception:
                pass
    elif kind == "speak":
        allow = band not in ("critical",)
        reason = "ok" if allow else f"band={band}"
    return {"allow": allow, "reason": reason, "snap": snap}


def record_fact(snap: dict[str, Any] | None = None) -> None:
    snap = snap or snapshot()
    slim = {
        "band": snap.get("band"),
        "gpu_temp": (snap.get("gpu") or {}).get("temp_c"),
        "vram_free": (snap.get("gpu") or {}).get("mem_free_mib"),
        "cpu_temp_c": snap.get("cpu_temp_c"),
        "llm_ok": snap.get("llm_ok"),
        "zulu": snap.get("zulu"),
    }
    db.put_fact("Ax-THERMAL", "metal-temp", json.dumps(slim)[:2000], kind="probe")
