"""Apply /wa link QR window support onto fieldkit nova/msg.py + term.py + deck. Run from kit root."""
from pathlib import Path
import re

MSG_LINK = r'''

def link_qr(channel: str = DEFAULT_CHANNEL, new_window: bool = True) -> dict:
    """Start WhatsApp (or other) QR login. Prefer a separate console window on Windows.

    Phone: WhatsApp → Settings → Linked Devices → Link a Device → scan.
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
    # Windows: dedicated console so ASCII/Unicode QR is scannable and not buried in TUI
    if new_window and sys.platform == "win32":
        # start opens a new window; /k keeps it open after login ends
        title = "NOVA WhatsApp QR — scan with phone"
        # Use cmd start with quoted title; call openclaw.CMD via PATH
        cmdline = f'start "{title}" cmd /k "openclaw channels login --channel {ch} & echo. & echo Scan with WhatsApp Linked Devices. Close when linked. & pause"'
        try:
            subprocess.Popen(cmdline, shell=True, cwd=os.path.expanduser("~"))
            return {
                "ok": True,
                "mode": "new_console",
                "channel": ch,
                "instruction": "Scan QR in the new window: WhatsApp → Linked Devices → Link a Device",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "fallback": "run openclaw channels login --channel whatsapp"}
    # Same-process fallback (TUI / Linux): stream login in foreground
    r = _cli("channels", "login", "--channel", ch, timeout=180.0)
    return {
        "ok": bool(r.get("ok")),
        "mode": "inline",
        "channel": ch,
        "stdout": r.get("stdout", "")[:2000],
        "stderr": r.get("stderr", "")[:1000],
        "instruction": "If QR missing, use /wa link (opens separate window on Windows)",
    }
'''

def patch_msg():
    p = Path("nova/msg.py")
    t = p.read_text(encoding="utf-8")
    if "def link_qr" in t:
        print("msg.link_qr already")
        return
    # append before end
    p.write_text(t.rstrip() + "\n" + MSG_LINK + "\n", encoding="utf-8")
    print("msg.link_qr added")


def patch_term():
    p = Path("nova/tui/term.py")
    t = p.read_text(encoding="utf-8")
    if 'sub in ("link", "qr"' in t or "sub in ('link', 'qr'" in t:
        print("term /wa link already")
        return
    # Insert link handling after status branch inside /wa block
    needle = '''        if sub in ("status", "st"):
            return str(nova_msg.status())'''
    insert = '''        if sub in ("status", "st"):
            return str(nova_msg.status())
        if sub in ("link", "qr", "login"):
            return str(nova_msg.link_qr(new_window=True))'''
    if needle not in t:
        raise SystemExit("term /wa status needle missing")
    t = t.replace(needle, insert, 1)
    t = t.replace(
        'return "usage: /wa status | /wa draft TEXT | /wa send dry TEXT | /wa send approve TEXT"',
        'return "usage: /wa status | /wa link | /wa draft TEXT | /wa send dry TEXT | /wa send approve TEXT"',
    )
    p.write_text(t, encoding="utf-8")
    print("term /wa link wired")


def patch_deck():
    import json
    p = Path("nova/gui/deck.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    for tile in data["tiles"]:
        if tile.get("id") == "whatsapp":
            tile["why"] = "Phone DM via OpenClaw. Chat: /wa link (QR window) | /wa status | /wa send approve TEXT"
            break
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("deck why updated")


if __name__ == "__main__":
    patch_msg()
    patch_term()
    patch_deck()
    print("PATCH_OK")
