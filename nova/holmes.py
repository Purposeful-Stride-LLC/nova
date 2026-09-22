"""Holmes + Watson L0 sweep — code only, no LLM.

Holmes: metal probes (hardware/process/network/lan/ai_runtime/volumes/vision)
Watson: efficient tree map of key Windows roots (fieldkit, NOVA docs, thumb, openclaw)
"""
from __future__ import annotations

import json
import time

from nova.db import insert_obs, put_fact, zulu


def sweep() -> dict:
    t0 = time.time()
    probes = []
    names = (
        "hardware",
        "process",
        "network",
        "lan",
        "ai_runtime",
        "volumes",
        "vision",
    )
    for name in names:
        try:
            from nova.awareness import run_probe

            row = run_probe(name)
        except Exception as exc:  # noqa: BLE001
            row = {"source": name, "ok": False, "error": str(exc)}
        probes.append(row)
        insert_obs(row.get("source", name), bool(row.get("ok")), json.dumps(row)[:2000])

    watson = {}
    try:
        from nova import watson as watson_mod

        watson = watson_mod.map_metal(max_depth=3)
    except Exception as exc:  # noqa: BLE001
        watson = {"ok": False, "error": str(exc)}

    out = {
        "zulu": zulu(),
        "duration_s": round(time.time() - t0, 3),
        "role": "holmes",
        "probes": probes,
        "watson": {
            "ok": watson.get("ok"),
            "artifact": watson.get("artifact"),
            "roots": [
                {"root": m.get("root"), "files": m.get("files"), "dirs": m.get("dirs"), "ok": m.get("ok")}
                for m in (watson.get("maps") or [])
            ],
        },
    }
    put_fact(
        "Ax-HOLMES",
        "sweep",
        json.dumps({
            "zulu": out["zulu"],
            "duration_s": out["duration_s"],
            "probe_ok": sum(1 for p in probes if p.get("ok")),
            "probe_n": len(probes),
            "watson": out["watson"],
        })[:4000],
        kind="crawl",
    )
    return out
