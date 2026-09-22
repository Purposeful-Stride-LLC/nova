"""Standard bug / tool-break reporting for the homestead spine.

Every hand and leash call should route failures here so:
  - facts get Tx-BREAK / Ax-BREAK stamps (WHI discipline)
  - rank-2 report cards open for steward HIL when severity >= warn
  - chronicler mail gets a break packet for audit

Severity: info | warn | error | fatal
"""

from __future__ import annotations

import json
import traceback
from typing import Any

from nova import db


def record(
    tool: str,
    err: str,
    *,
    severity: str = "error",
    whi: str = "Tx-BREAK",
    cite: str = "",
    context: dict[str, Any] | None = None,
    open_report: bool = True,
) -> dict:
    severity = (severity or "error").lower()
    payload = {
        "zulu": db.zulu(),
        "tool": tool,
        "severity": severity,
        "err": (err or "")[:1500],
        "cite": cite,
        "context": context or {},
    }
    title = f"{severity}:{tool}"[:160]
    body = json.dumps(payload, ensure_ascii=False)[:8000]
    db.put_fact(whi, title, body)
    rid = None
    if open_report and severity in {"warn", "error", "fatal"}:
        from nova import office

        rank = 1 if severity == "warn" else 2 if severity == "error" else 3
        rid = office.report(rank, f"tool break: {tool}", body[:2000])
        try:
            office.post_packet(
                dest="chronicler@local",
                mask="chronicler",
                whi=whi,
                kind="break",
                cite=cite or tool,
                body=body[:3500],
            )
        except Exception:
            pass
    return {"ok": False, "tool": tool, "severity": severity, "report": rid, "whi": whi}


def wrap(tool: str, fn, *args, severity: str = "error", **kwargs):
    """Run fn; on exception record break and return dict."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        return record(
            tool,
            str(exc),
            severity=severity,
            cite=tool,
            context={"trace": traceback.format_exc()[-1200:]},
        )
