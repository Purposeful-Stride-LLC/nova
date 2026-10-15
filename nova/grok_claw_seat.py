"""Council seat registration for grok@claw (PROTOCOL_CLAW_GROK_COM)."""
from __future__ import annotations

MASK = "grok@claw"
PARENT = "openclaw@local"
PROTOCOL = "PROTOCOL_CLAW_GROK_COM"


def ensure_seat() -> dict:
    """Upsert employee grok@claw via office if available."""
    from nova import db, office

    try:
        if hasattr(office, "ensure_employee"):
            office.ensure_employee(
                "grok@claw", role="external-grok-browser", parent="openclaw@local"
            )
            mode = "office"
        elif hasattr(office, "upsert_employee"):
            office.upsert_employee("grok@claw")
            mode = "office"
        else:
            mode = "fact-only"
        body = (
            "protocol=PROTOCOL_CLAW_GROK_COM\n"
            "parent=openclaw@local\n"
            "role=council-visiting-minister"
        )
        db.put_fact("Ax-CLAW", "seat:grok@claw", body, kind="claw")
        return {"ok": True, "mode": mode, "mask": MASK}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "mask": MASK}


def opinion(query: str, *, dry_run: bool = True) -> dict:
    """Council entry: one opinion via leash.grok_query."""
    from nova import leash

    ensure_seat()
    return leash.grok_query(query, dry_run=dry_run, deliver=not dry_run)
