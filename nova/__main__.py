"""python -m nova — daemon. TUI attaches separately."""

from __future__ import annotations

import time

from nova import db, sched


def main() -> None:
    db.connect().close()
    print(f"NOVA daemon {db.zulu()} db={db.db_path()}")
    print("jobs:", [f"{j['id']}:{j['name']}/{j['every_s']}s en={j['enabled']}" for j in db.jobs()])
    print("Ctrl+C stops.  python -m nova.tui")
    while True:
        for res in sched.tick():
            print(res)
        time.sleep(5)


if __name__ == "__main__":
    main()
