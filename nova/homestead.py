"""Homestead jack-in protocol: scan metal -> identify need -> forge -> wire.

Captures steward + Aurelius (lobster) + Qwen (komodo) with the operator:
NOVA pokes the host until it can live there — codesum, probes, spider, WHI —
without pretending thumb shards are already unified.
"""
from __future__ import annotations

import json
from pathlib import Path
from nova import db

DEFAULT_THUMB_AI = Path(r"D:\pg\ai")
DEFAULT_FIELDKIT = Path.home() / "Documents" / "NOVA" / "NOVA_fieldkit_v1_4"

SHARD_MAP = {
    "awareness": [
        "holmes.py", "hardware_probe.py", "lan_probe.py", "master_probe.py",
        "software_inventory.py", "system_doc.py", "system_spec.py",
    ],
    "spider": [
        "mylilspider.py", "network_spyder.py", "network_spyder2.py", "network_probe.py",
    ],
    "codesum": ["cbSum.py", "cbSumcolor.py", "codebase_1.txt"],
    "whi": ["hexclass.txt"],
    "tts": ["speak_phrases.sh", "nova-ai/pocket-tts.txt", "nova-ai/nova_tts.py"],
    "orchestrator": ["nova-ai/orchestrator.py", "nova-ai/ai_main.py", "nova-ai/nova_Tv3.py"],
    "docs": ["nova-ai/project_docs", "AI_tool_kit.txt", "cronjob.txt"],
}


def scan_thumb(root: Path | None = None) -> dict:
    root = Path(root or DEFAULT_THUMB_AI)
    found, missing = {}, {}
    if not root.exists():
        return {"ok": False, "error": "missing %s" % root, "root": str(root)}
    for wing, names in SHARD_MAP.items():
        hit, miss = [], []
        for name in names:
            p = root / name
            if p.exists():
                hit.append(str(p))
            else:
                miss.append(name)
        found[wing] = hit
        missing[wing] = miss
    body = {
        "ok": True,
        "zulu": db.zulu(),
        "root": str(root),
        "found": {k: len(v) for k, v in found.items()},
        "paths": found,
        "missing": missing,
    }
    db.put_fact(
        "Ax-HOMESTEAD",
        "thumb-scan",
        json.dumps({k: body[k] for k in ("ok", "zulu", "root", "found")})[:4000],
        kind="crawl",
    )
    return body


def identify_needs(scan: dict, fieldkit: Path | None = None) -> list[dict]:
    fieldkit = Path(fieldkit or DEFAULT_FIELDKIT)
    needs = []
    paths = scan.get("paths") or {}
    if paths.get("awareness"):
        needs.append({
            "id": "need-l0-probes",
            "why": "Thumb has holmes/lan/hardware probes; glass L0 wants castle awareness",
            "forge": "Port lean probes into nova/awareness/ or expand sched.holmes",
            "sources": paths.get("awareness", [])[:6],
        })
    if paths.get("spider"):
        needs.append({
            "id": "need-spider-parity",
            "why": "mylilspider/network_spyder heritage; metal has crawl+ingest_pipe",
            "forge": "Diff delay/UA/strip; keep metal pipe; steal missing politeness",
            "sources": paths.get("spider", [])[:4],
        })
    if paths.get("codesum"):
        needs.append({
            "id": "need-codesum-homestead",
            "why": "cbSum lineage = scan codebase to jack in; metal hands/codesum exists",
            "forge": "Run codesum on thumb+fieldkit; promote worth-keep Tx-CODE to live",
            "sources": paths.get("codesum", [])[:3],
        })
    if paths.get("whi"):
        needs.append({
            "id": "need-hexclass-align",
            "why": "hexclass.txt is WHI ancestor",
            "forge": "Diff vs nova/whi.py; fold missing codes",
            "sources": paths.get("whi", [])[:2],
        })
    needs.append({
        "id": "need-protocol-loop",
        "why": "Automate identify-need -> forge -> jack-in as standing protocol",
        "forge": "homestead.cycle job: scan -> needs -> mail Aurelius+Qwen STEPs (HIL)",
        "sources": [],
    })
    db.put_fact("Ax-HOMESTEAD", "needs", json.dumps(needs)[:4000], kind="crawl")
    return needs


def cycle() -> dict:
    from nova import thermal

    scan = scan_thumb()
    needs = identify_needs(scan) if scan.get("ok") else []
    therm = thermal.snapshot()
    thermal.record_fact(therm)
    # Thermal need if hot
    if therm.get("band") in ("hot", "very_hot", "critical"):
        needs.append({
            "id": "need-thermal-cool",
            "why": f"GPU band={therm.get('band')} temp={(therm.get('gpu') or {}).get('temp_c')}",
            "forge": "Pause LLM jobs; L0 only until cool; check fans/dust",
            "sources": [],
        })
    out = {
        "ok": bool(scan.get("ok")),
        "scan": {"found": scan.get("found"), "root": scan.get("root")},
        "needs": needs,
        "thermal": {
            "band": therm.get("band"),
            "gpu_temp": (therm.get("gpu") or {}).get("temp_c"),
            "vram_free": (therm.get("gpu") or {}).get("mem_free_mib"),
            "llm_ok": therm.get("llm_ok"),
        },
        "zulu": db.zulu(),
    }
    db.put_fact(
        "Ax-HOMESTEAD",
        "cycle",
        json.dumps({"ok": out["ok"], "n_needs": len(needs), "thermal": out.get("thermal"), "zulu": out["zulu"]})[:2000],
        kind="crawl",
    )
    return out
