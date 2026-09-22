"""Lean outbound messaging via OpenClaw channels. HIL by default.

NOVA does not reinvent WhatsApp - Claw already has the Web session.
This module is the thin tentacle: status, draft, send(approve=True).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from nova import db

DEFAULT_CHANNEL = "whatsapp"
OPENCLAW = shutil.which("openclaw") or r"C:\Users\wuchy\AppData\Roaming\npm\openclaw.CMD"


def _cli(*args: str, timeout: float = 60.0) -> dict[str, Any]:
    if not OPENCLAW:
        return {"ok": False, "error": "openclaw CLI not found"}
    try:
        p = subprocess.run(
            [OPENCLAW, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    return {
        "ok": p.returncode == 0,
        "code": p.returncode,
        "stdout": out[:4000],
        "stderr": err[:2000],
    }


def status() -> dict[str, Any]:
    """Gateway channel status (WhatsApp link health)."""
    r = _cli("channels", "status", timeout=45)
    text = (r.get("stdout") or "") + "\n" + (r.get("stderr") or "")
    linked = "not linked" not in text.lower() and "linked" in text.lower()
    # more reliable flags
    stopped = "stopped" in text.lower()
    not_linked = "not linked" in text.lower()
    enabled = "whatsapp" in text.lower() and "enabled" in text.lower()
    body = {
        "ok": bool(r.get("ok")),
        "enabled": enabled,
        "linked": (not not_linked) and enabled,
        "stopped": stopped,
        "raw_head": text[:800],
        "hint": "openclaw channels login --channel whatsapp" if not_linked else "",
    }
    db.put_fact("Ax-MSG", "wa-status", json.dumps(body, ensure_ascii=False)[:4000])
    return body


def default_target() -> str:
    """First allowFrom number from openclaw.json, as +E.164 when possible."""
    from pathlib import Path

    cfg = Path.home() / ".openclaw" / "openclaw.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    allow = (data.get("channels") or {}).get("whatsapp", {}).get("allowFrom") or []
    if not allow:
        return ""
    n = str(allow[0]).strip()
    if n.startswith("+"):
        return n
    if n.isdigit():
        return "+" + n
    return n


def draft(message: str, target: str | None = None, channel: str = DEFAULT_CHANNEL) -> dict[str, Any]:
    """Build send payload; never sends."""
    tgt = (target or default_target()).strip()
    msg = (message or "").strip()
    payload = {
        "channel": channel,
        "target": tgt,
        "message": msg[:3500],
        "approve_required": True,
    }
    db.put_fact(
        "Tx-MSG",
        f"draft:{channel}",
        json.dumps(payload, ensure_ascii=False)[:4000],
    )
    return {"ok": True, **payload}


def send(
    message: str,
    target: str | None = None,
    channel: str = DEFAULT_CHANNEL,
    approve: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Send via OpenClaw. Requires approve=True unless dry_run (prints only).

    Leaner than raw Claw agent chat: one CLI call, palace stamp, no tool soup.
    """
    tgt = (target or default_target()).strip()
    msg = (message or "").strip()
    if not msg:
        return {"ok": False, "error": "empty message"}
    if not tgt:
        return {"ok": False, "error": "no target (set allowFrom or pass target=)"}
    if not approve and not dry_run:
        d = draft(msg, tgt, channel)
        d["ok"] = False
        d["error"] = "HIL: pass approve=True to send (or dry_run=True)"
        return d
    args = [
        "message",
        "send",
        "--channel",
        channel,
        "--target",
        tgt,
        "--message",
        msg,
        "--json",
    ]
    if dry_run:
        args.append("--dry-run")
    r = _cli(*args, timeout=90)
    stamp = {
        "zulu": db.zulu(),
        "channel": channel,
        "target": tgt,
        "message_head": msg[:120],
        "dry_run": dry_run,
        "approve": approve,
        "cli": {"ok": r.get("ok"), "code": r.get("code"), "stdout": r.get("stdout", "")[:1500], "stderr": r.get("stderr", "")[:800]},
    }
    whi = "Ax-MSG" if r.get("ok") else "Tx-MSG"
    db.put_fact(whi, f"send:{channel}", json.dumps(stamp, ensure_ascii=False)[:4000])
    return {"ok": bool(r.get("ok")), **stamp}


def link_qr(channel: str = DEFAULT_CHANNEL, new_window: bool = True) -> dict:
    """Start WhatsApp QR login in a separate Windows console when possible.

    Phone: WhatsApp -> Settings -> Linked Devices -> Link a Device -> scan.
    QR expires ~60s; re-run /wa link if needed. Does not send messages.
    """
    import sys
    import os

    ch = (channel or DEFAULT_CHANNEL).strip().lower()
    if not OPENCLAW:
        return {"ok": False, "error": "openclaw CLI not found"}
    db.put_fact(
        "Tx-MSG",
        f"link-qr:{ch}",
        f"zulu={db.zulu()} window={new_window} hint=scan Linked Devices",
    )
    if new_window and sys.platform == "win32":
        title = "NOVA WhatsApp QR - scan with phone"
        cmdline = (
            f'start "{title}" cmd /k '
            f'"openclaw channels login --channel {ch} '
            f'& echo. & echo Scan with WhatsApp Linked Devices. Close when linked. & pause"'
        )
        try:
            subprocess.Popen(cmdline, shell=True, cwd=os.path.expanduser("~"))
            return {
                "ok": True,
                "mode": "new_console",
                "channel": ch,
                "instruction": "Scan QR in the new window: WhatsApp -> Linked Devices -> Link a Device",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    r = _cli("channels", "login", "--channel", ch, timeout=180.0)
    return {
        "ok": bool(r.get("ok")),
        "mode": "inline",
        "channel": ch,
        "stdout": (r.get("stdout") or "")[:2000],
        "stderr": (r.get("stderr") or "")[:1000],
    }

