"""Council series stub — agenda only unless STEWARD_RUN=1.

Thermal-polite: never loads an LLM by default. Writes NEXT_TOPIC / seed files
under STAGING/council_series/ for Claw or steward to execute later.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SERIES = list("ABCDEFGHI")
TITLES = {
    "A": "Beacon/tentacle always-on",
    "B": "Mail/job schema + waiting queue",
    "C": "Education seed series",
    "D": "WHI gap scout → search → ingest",
    "E": "Leash Komodo→Claw forge",
    "F": "Paper markets skeleton",
    "G": "User-facing HIL/ear/diary/GUI",
    "H": "GitHub sync cadence",
    "I": "Recursive schedule health",
}


def _kit_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _series_dir() -> Path:
    d = _kit_root() / "STAGING" / "council_series"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _zulu() -> str:
    try:
        from nova import db

        return db.zulu()
    except Exception:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_next() -> dict:
    path = _series_dir() / "NEXT_TOPIC.json"
    if not path.is_file():
        return {"topic": "A", "title": TITLES["A"], "mode": "agenda-only"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"topic": "A", "title": TITLES["A"], "mode": "agenda-only", "parse_error": True}


def advance_topic(cur: str) -> str:
    cur = (cur or "A").upper()[:1]
    if cur not in SERIES:
        return "A"
    i = SERIES.index(cur)
    return SERIES[min(i + 1, len(SERIES) - 1)] if i < len(SERIES) - 1 else "A"


def write_agenda(topic: str | None = None) -> dict:
    """Write/refresh NEXT_TOPIC + Ax-HOMESTEAD seed text. No LLM."""
    d = _series_dir()
    prev = read_next()
    topic = (topic or prev.get("topic") or "A").upper()[:1]
    if topic not in TITLES:
        topic = "A"
    gaps_path = d / "PROOF_GAPS.json"
    gaps: list = []
    if gaps_path.is_file():
        try:
            gaps = json.loads(gaps_path.read_text(encoding="utf-8")).get("gaps") or []
        except Exception:
            gaps = []
    prior = [g for g in gaps if g.get("phase") == topic][:5]
    body = {
        "topic": topic,
        "title": TITLES[topic],
        "phase": topic,
        "zulu": _zulu(),
        "mode": "agenda-only",
        "model_hint": "qwen2:0.5b",
        "require_steward_run": True,
        "prior_proof_gaps_file": "STAGING/council_series/PROOF_GAPS.json",
        "prior_gaps_for_topic": prior,
        "output_json": f"STAGING/council_series/COUNCIL_{topic}_RESULT.json",
        "ax_homestead_seed_out": f"STAGING/council_series/AX_HOMESTEAD_{topic}.txt",
        "next_after_this": advance_topic(topic),
    }
    out = d / "NEXT_TOPIC.json"
    out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    seed = (
        f"Ax-HOMESTEAD council seed\nTopic: {topic} {TITLES[topic]}\n"
        f"Zulu: {body['zulu']}\n"
        f"Mode: agenda-only (no LLM unless STEWARD_RUN=1)\n"
        f"Prior gaps: {json.dumps(prior)[:500]}\n"
        f"Next after this: {body['next_after_this']}\n"
    )
    seed_path = d / f"AX_HOMESTEAD_{topic}.txt"
    seed_path.write_text(seed, encoding="utf-8")
    try:
        from nova import db

        db.put_fact("Ax-HOMESTEAD", f"council-agenda-{topic}", seed[:3500])
    except Exception:
        pass
    return {
        "ok": True,
        "mode": "agenda-only",
        "topic": topic,
        "path": str(out),
        "seed": str(seed_path),
        "bytes": out.stat().st_size,
    }


def run_stub() -> dict:
    """Sched entry: agenda only unless STEWARD_RUN=1 (still no auto chamber)."""
    steward = os.environ.get("STEWARD_RUN", "").strip().lower() in ("1", "true", "yes")
    agenda = write_agenda()
    if not steward:
        agenda["note"] = "agenda-only; set STEWARD_RUN=1 to allow live council later"
        return agenda
    d = _series_dir()
    req = {
        "zulu": _zulu(),
        "topic": agenda.get("topic"),
        "action": "steward_or_claw_may_run_chamber",
        "model_hint": "qwen2:0.5b",
        "thermal_gate": True,
        "cite": "STAGING/COUNCIL_SERIES_SCHEDULE.md",
    }
    rp = d / "RUN_REQUEST.json"
    rp.write_text(json.dumps(req, indent=2) + "\n", encoding="utf-8")
    agenda["steward_run"] = True
    agenda["run_request"] = str(rp)
    agenda["note"] = "STEWARD_RUN=1: wrote RUN_REQUEST.json (no LLM in stub)"
    return agenda


__all__ = ["run_stub", "write_agenda", "read_next"]
