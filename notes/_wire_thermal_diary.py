# -*- coding: utf-8 -*-
"""Write thermal.py, novadiary.py; patch homestead, office, sched, docs_ingest."""
from pathlib import Path
import ast

kit = Path(r"C:\Users\wuchy\Documents\NOVA\NOVA_fieldkit_v1_4")

thermal_src = r'''"""L0 thermal + VRAM gate for shared NVIDIA metal. No LLM."""
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
'''

(kit / "nova" / "thermal.py").write_text(thermal_src, encoding="utf-8")
ast.parse(thermal_src)
print("wrote thermal.py")

diary_src = r'''"""Nova diary — a few sweet tokens, chronicler-mask, append-only.

Writes:
  - nova-out/DIARY.md (running journal)
  - C:\\Users\\wuchy\\Documents\\NOVA\\GrokBot.log.ai (steward mirror)
  - Tx-DIARY fact in palace
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nova import db

DIARY_MD = Path(r"C:\Users\wuchy\Documents\NOVA\NOVA_fieldkit_v1_4\nova-out\DIARY.md")
STEWARD_LOG = Path(r"C:\Users\wuchy\Documents\NOVA\GrokBot.log.ai")


def _prompt(theme: str, context: str) -> str:
    return (
        "You are NOVA writing a short personal diary entry (4-8 sentences). "
        "Warm, observant, lightly poetic but concrete. First person. "
        "Mention what you learned or noticed today about the palace / metal / people. "
        f"Theme: {theme}\n"
        f"Context notes:\n{context[:1800]}\n"
        "Write only the diary entry, no title header."
    )


def write_entry(
    theme: str = "evening homestead",
    context: str = "",
    model: str = "qwen2:0.5b",
    mask: str = "chronicler",
) -> dict[str, Any]:
    from nova import thermal
    from nova import ingest_pipe

    g = thermal.gate("llm")
    if not g.get("allow"):
        return {"ok": False, "error": "thermal_deny", "gate": g.get("reason"), "snap": g.get("snap")}

    if not context:
        # pull a few live doc titles / thermal for flavor
        bits = []
        try:
            snap = g.get("snap") or thermal.snapshot()
            gpu = snap.get("gpu") or {}
            bits.append(
                f"GPU {gpu.get('temp_c')}C band={snap.get('band')} "
                f"VRAM free={gpu.get('mem_free_mib')}"
            )
        except Exception:
            pass
        try:
            con = db.connect()
            live = con.execute("SELECT COUNT(*) c FROM chunks WHERE status='live'").fetchone()["c"]
            doc = con.execute(
                "SELECT COUNT(*) c FROM chunks WHERE status='live' AND whi='0x-DOC'"
            ).fetchone()["c"]
            bits.append(f"palace live={live} 0x-DOC={doc}")
        except Exception:
            pass
        context = "; ".join(bits) or "quiet metal"

    prompt = _prompt(theme, context)
    # Prefer ingest_pipe.summarize if available; else ollama_talk
    text = ""
    err = ""
    try:
        r = ingest_pipe.summarize(prompt, model=model, mask=mask)
        if isinstance(r, dict):
            if r.get("ok"):
                text = (r.get("summary") or "").strip()
            else:
                err = str(r.get("error") or "summarize_fail")
        else:
            text = str(r).strip()
    except Exception as exc:
        err = str(exc)
        try:
            from nova import ollama_talk

            text = (ollama_talk.chat(model, prompt) or "").strip()
            err = ""
        except Exception as exc2:
            err = f"{err}; {exc2}"

    if not text:
        return {"ok": False, "error": err or "empty"}

    zulu = db.zulu()
    block = f"\n## {zulu}\n{text}\n"
    DIARY_MD.parent.mkdir(parents=True, exist_ok=True)
    with DIARY_MD.open("a", encoding="utf-8") as f:
        f.write(block)
    try:
        with STEWARD_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{zulu}] NOVA DIARY: {text[:500]}\n")
    except Exception:
        pass
    db.put_fact("Tx-DIARY", f"diary:{zulu[:16]}", text[:3500], kind="diary")
    return {"ok": True, "zulu": zulu, "chars": len(text), "path": str(DIARY_MD), "preview": text[:240]}
'''

(kit / "nova" / "novadiary.py").write_text(diary_src, encoding="utf-8")
ast.parse(diary_src)
print("wrote novadiary.py")

# Patch homestead.cycle to include thermal
hp = kit / "nova" / "homestead.py"
hs = hp.read_text(encoding="utf-8")
if "thermal.snapshot" not in hs:
    hs = hs.replace(
        "def cycle() -> dict:\n    scan = scan_thumb()\n    needs = identify_needs(scan) if scan.get(\"ok\") else []\n    out = {\n        \"ok\": bool(scan.get(\"ok\")),\n        \"scan\": {\"found\": scan.get(\"found\"), \"root\": scan.get(\"root\")},\n        \"needs\": needs,\n        \"zulu\": db.zulu(),\n    }\n",
        "def cycle() -> dict:\n    from nova import thermal\n\n    scan = scan_thumb()\n    needs = identify_needs(scan) if scan.get(\"ok\") else []\n    therm = thermal.snapshot()\n    thermal.record_fact(therm)\n    # Thermal need if hot\n    if therm.get(\"band\") in (\"hot\", \"very_hot\", \"critical\"):\n        needs.append({\n            \"id\": \"need-thermal-cool\",\n            \"why\": f\"GPU band={therm.get('band')} temp={(therm.get('gpu') or {}).get('temp_c')}\",\n            \"forge\": \"Pause LLM jobs; L0 only until cool; check fans/dust\",\n            \"sources\": [],\n        })\n    out = {\n        \"ok\": bool(scan.get(\"ok\")),\n        \"scan\": {\"found\": scan.get(\"found\"), \"root\": scan.get(\"root\")},\n        \"needs\": needs,\n        \"thermal\": {\n            \"band\": therm.get(\"band\"),\n            \"gpu_temp\": (therm.get(\"gpu\") or {}).get(\"temp_c\"),\n            \"vram_free\": (therm.get(\"gpu\") or {}).get(\"mem_free_mib\"),\n            \"llm_ok\": therm.get(\"llm_ok\"),\n        },\n        \"zulu\": db.zulu(),\n    }\n",
    )
    # also enrich put_fact
    hs = hs.replace(
        'json.dumps({"ok": out["ok"], "n_needs": len(needs), "zulu": out["zulu"]})[:2000]',
        'json.dumps({"ok": out["ok"], "n_needs": len(needs), "thermal": out.get("thermal"), "zulu": out["zulu"]})[:2000]',
    )
    hp.write_text(hs, encoding="utf-8")
    ast.parse(hs)
    print("patched homestead")
else:
    print("homestead already thermal")

# Patch office.snapshot_hw to include gpu thermal
op = kit / "nova" / "office.py"
osrc = op.read_text(encoding="utf-8")
if "thermal.snapshot" not in osrc:
    needle = '    blob["cams"] = cams\n    raw = json.dumps(blob, sort_keys=True)'
    insert = '''    blob["cams"] = cams
    try:
        from nova import thermal

        th = thermal.snapshot()
        blob["thermal"] = {
            "band": th.get("band"),
            "gpu_temp_c": (th.get("gpu") or {}).get("temp_c"),
            "gpu_util": (th.get("gpu") or {}).get("util_pct"),
            "vram_used_mib": (th.get("gpu") or {}).get("mem_used_mib"),
            "vram_free_mib": (th.get("gpu") or {}).get("mem_free_mib"),
            "cpu_temp_c": th.get("cpu_temp_c"),
            "llm_ok": th.get("llm_ok"),
        }
    except Exception as exc:
        blob["thermal"] = {"error": str(exc)}
    raw = json.dumps(blob, sort_keys=True)'''
    if needle not in osrc:
        raise SystemExit("office snapshot needle missing")
    osrc = osrc.replace(needle, insert)
    op.write_text(osrc, encoding="utf-8")
    ast.parse(osrc)
    print("patched office.snapshot_hw")
else:
    print("office already thermal")

# Patch sched docs-ingest + ingest-drain + add diary + thermal-check
sp = kit / "nova" / "sched.py"
ss = sp.read_text(encoding="utf-8")
if "thermal.gate" not in ss:
    ss = ss.replace(
        '''        elif key == "docs-ingest":
            from nova import docs_ingest
            d = docs_ingest.ingest_due(limit=1, model="qwen2:0.5b", mask="chronicler")
            note = f"n={d.get('n')} ok={d.get('ok')}"
        elif key == "ingest-drain":
            from nova import crawl
            d = crawl.drain_temps_through_pipe(limit=8, model="qwen2:0.5b", mask="chronicler", min_score=28)
            note = "drain_n=" + str((d or {}).get("n"))
''',
        '''        elif key == "docs-ingest":
            from nova import docs_ingest, thermal
            g = thermal.gate("llm")
            if not g.get("allow"):
                note = f"thermal_skip {g.get('reason')} band={(g.get('snap') or {}).get('band')}"
            else:
                band = (g.get("snap") or {}).get("band")
                lim = 2 if band == "cool" else 1
                d = docs_ingest.ingest_due(limit=lim, model="qwen2:0.5b", mask="chronicler")
                note = f"n={d.get('n')} ok={d.get('ok')} band={band}"
        elif key == "ingest-drain":
            from nova import crawl, thermal
            g = thermal.gate("llm")
            if not g.get("allow"):
                note = f"thermal_skip {g.get('reason')}"
            else:
                band = (g.get("snap") or {}).get("band")
                lim = 8 if band == "cool" else 4
                d = crawl.drain_temps_through_pipe(limit=lim, model="qwen2:0.5b", mask="chronicler", min_score=28)
                note = "drain_n=" + str((d or {}).get("n")) + f" band={band}"
        elif key == "nova-diary":
            from nova import novadiary
            d = novadiary.write_entry(theme="homestead evening")
            note = f"ok={d.get('ok')} chars={d.get('chars')} err={d.get('error')}"
        elif key == "thermal-check":
            from nova import thermal
            snap = thermal.snapshot()
            thermal.record_fact(snap)
            note = f"band={snap.get('band')} temp={(snap.get('gpu') or {}).get('temp_c')} llm_ok={snap.get('llm_ok')}"
''',
    )
    # homestead note include thermal
    if 'note = f"needs={len(cyc.get(\'needs\') or [])} root={(cyc.get(\'scan\') or {}).get(\'root\')}"' in ss:
        ss = ss.replace(
            'note = f"needs={len(cyc.get(\'needs\') or [])} root={(cyc.get(\'scan\') or {}).get(\'root\')}"',
            'th = cyc.get("thermal") or {}\n            note = f"needs={len(cyc.get(\'needs\') or [])} band={th.get(\'band\')} temp={th.get(\'gpu_temp\')} root={(cyc.get(\'scan\') or {}).get(\'root\')}"',
        )
    sp.write_text(ss, encoding="utf-8")
    ast.parse(ss)
    print("patched sched")
else:
    print("sched already thermal")

print("DONE WRITE")