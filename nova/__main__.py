"""python -m nova — daemon (fieldkit 2.1). TUI/GUI attach separately and only PROPOSE.

Staged-install guard: if the kit carries a STAGED marker, the daemon refuses to start unless
NOVA_HOME is set explicitly and points inside a folder that is not a live install (no live data).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from nova import __version__, db, sched

KIT = Path(__file__).resolve().parent.parent


def staged_guard() -> str | None:
    if not (KIT / "STAGED").is_file():
        return None
    home = os.environ.get("NOVA_HOME")
    if not home:
        return "STAGED kit: refusing to start without an explicit NOVA_HOME (scratch data only)."
    allowed = [s.strip() for s in (KIT / "STAGED").read_text(encoding="utf-8").splitlines() if s.strip() and not s.startswith("#")]
    h = Path(home).resolve()
    if not any(h == (KIT / a).resolve() or str(h).startswith(str((KIT / a).resolve())) for a in allowed):
        return f"STAGED kit: NOVA_HOME is not one of the scratch homes listed in STAGED ({allowed})."
    return None


def main() -> None:
    why = staged_guard()
    if why:
        print(why)
        sys.exit(3)
    db.connect().close()
    print(f"NOVA daemon {__version__} {db.zulu()} db={db.db_path()}")
    try:  # moved here from the GUI refresh (2.1): workforce upsert once, at daemon start
        from nova import office
        office.ensure_workforce()
    except Exception as exc:
        print("workforce:", exc)
    if not any(j["name"] == "task-stimulus" for j in db.jobs()):
        db.job_ensure("task-stimulus", 600, enabled=1)
    print(sched.table_text())
    print("Ctrl+C stops.  python -m nova.tui   |  proposals: /cmd list")
    while True:
        for res in sched.tick():
            print(res)
        time.sleep(5)


if __name__ == "__main__":
    main()
