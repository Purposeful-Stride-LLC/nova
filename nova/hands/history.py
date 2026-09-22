"""Copy-locked browser History SQLite → Tx-HIST URLs. Steward then /web the keepers."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from nova import db


def _candidates() -> list[Path]:
    local = os.environ.get("LOCALAPPDATA") or ""
    home = Path.home()
    paths = []
    if local:
        paths += [
            Path(local) / "Google/Chrome/User Data/Default/History",
            Path(local) / "Microsoft/Edge/User Data/Default/History",
            Path(local) / "BraveSoftware/Brave-Browser/User Data/Default/History",
        ]
    paths += [
        home / ".config/google-chrome/Default/History",
        home / ".config/chromium/Default/History",
        home / "Library/Application Support/Google/Chrome/Default/History",
    ]
    return [p for p in paths if p.is_file()]


def ingest(limit: int = 80) -> dict:
    found = _candidates()
    if not found:
        return {"ok": False, "error": "no Chrome/Edge History file"}
    src = found[0]
    tmp = Path(tempfile.gettempdir()) / "nova_browser_history.db"
    shutil.copy2(src, tmp)
    con = sqlite3.connect(tmp)
    try:
        rows = con.execute(
            """SELECT url, title, last_visit_time
               FROM urls ORDER BY last_visit_time DESC LIMIT ?""",
            (int(limit),),
        ).fetchall()
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc), "src": str(src)}
    finally:
        con.close()
    dest = db.home() / "data" / "artifacts" / "history_urls.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for url, title, _ts in rows:
        title = (title or "")[:80]
        lines.append(f"{url}\t{title}")
        db.put_fact("Tx-HIST", title or url[:80], url)
    dest.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "src": str(src), "n": len(lines), "path": str(dest), "whi": "Tx-HIST"}
