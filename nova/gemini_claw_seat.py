"""Council seat registration for gemini@claw (PROTOCOL_CLAW_GEMINI_GOOGLE)."""
from __future__ import annotations

MASK = "gemini@claw"
PARENT = "openclaw@local"
PROTOCOL = "PROTOCOL_CLAW_GEMINI_GOOGLE"


def ensure_seat() -> dict:
    """Upsert employee gemini@claw via office if available."""
    from nova import db, office

    try:
        if hasattr(office, "ensure_employee"):
            office.ensure_employee(
                "gemini@claw", role="external-gemini-browser", parent="openclaw@local"
            )
            mode = "office"
        elif hasattr(office, "upsert_employee"):
            office.upsert_employee("gemini@claw")
            mode = "office"
        else:
            mode = "fact-only"
        body = (
            "protocol=PROTOCOL_CLAW_GEMINI_GOOGLE\n"
            "parent=openclaw@local\n"
            "role=council-visiting-minister\n"
            "path=steward-cdp-first (EVAL_GROK_CLAW_PERF NO-GO unattended native)\n"
        )
        db.put_fact("Ax-CLAW", "seat:gemini@claw", body, kind="claw")
        return {"ok": True, "mode": mode, "mask": MASK}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "mask": MASK}


def opinion(query: str, *, dry_run: bool = True, steward_cdp: bool = True) -> dict:
    """Council entry: one opinion via leash.gemini_query.

    Default steward_cdp=True (eval gate: steward-CDP first-class; native unattended NO-GO).
    """
    from nova import leash

    ensure_seat()
    return leash.gemini_query(
        query, dry_run=dry_run, deliver=not dry_run, steward_cdp=steward_cdp
    )
