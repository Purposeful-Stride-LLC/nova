"""Open WhatsApp QR login in a new console window.
Usage: python -m nova.gui.wa_qr_window
"""
from __future__ import annotations

def main() -> None:
    from nova import msg
    print(msg.link_qr(new_window=True))

if __name__ == "__main__":
    main()
