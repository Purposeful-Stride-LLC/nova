"""Holmes sweep — uses awareness probes if present."""

from __future__ import annotations

import json
import time

from nova.db import insert_obs, zulu


def sweep() -> dict:
    t0 = time.time()
    probes = []
    names = (
        "hardware",
        "vision",
        "process",
        "network",
        "lan",
        "ai_runtime",
        "volumes",
    )
    for name in names:
        try:
            from nova.awareness import run_probe

            row = run_probe(name)
        except Exception as exc:  # noqa: BLE001
            row = {"source": name, "ok": False, "error": str(exc)}
        probes.append(row)
        insert_obs(row.get("source", name), bool(row.get("ok")), json.dumps(row)[:2000])
    return {
        "zulu": zulu(),
        "duration_s": round(time.time() - t0, 3),
        "probes": probes,
    }
