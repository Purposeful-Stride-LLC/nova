#!/usr/bin/env python3
"""Fieldkit 2.0 open-gap smoke — mail tool, forge_step, put_fact wings, clear-ingest dry-run."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn):
        try:
            fn()
            results.append((name, True, "ok"))
            print(f"PASS  {name}")
        except Exception as exc:
            results.append((name, False, str(exc)))
            print(f"FAIL  {name}: {exc}")
            traceback.print_exc()

    tmp = Path(tempfile.mkdtemp(prefix="nova_fk2_open_"))
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    os.environ["NOVA_HOME"] = str(tmp)
    sys.path.insert(0, str(ROOT))
    print(f"NOVA_HOME={tmp}")

    def t_mail_import():
        from nova.mail.claw_mail_tool import (
            dry_run_ping,
            health,
            ping,
            poll_mail,
            send_job,
        )
        from nova.mail.tentacle_client import default_client

        assert callable(ping) and callable(health) and callable(send_job)
        stub = poll_mail()
        assert stub.get("ok") is True
        assert isinstance(stub.get("queued"), list)
        c = default_client()
        assert c.host == "192.0.2.10"
        # dry_run_ping may fail offline — just must return dict with ok key
        probe = dry_run_ping(timeout=2.0)
        assert "ok" in probe and "reachable" in probe

    check("mail claw_mail_tool import+stub", t_mail_import)

    def t_forge_step():
        from nova.leash import forge_step

        outbox = tmp / "nova-out"
        outbox.mkdir(parents=True, exist_ok=True)
        artifact = outbox / "open_smoke.txt"
        artifact.write_text("open-gap-smoke\n", encoding="utf-8")
        step = tmp / "STEP_OPEN.txt"
        step.write_text("GOAL: open\nFILES: open_smoke.txt\nDONE when: proof\n", encoding="utf-8")
        env = forge_step(step, outbox=outbox)
        assert env.get("ok") is True
        assert int(env.get("bytes_total") or 0) > 0

    check("forge_step", t_forge_step)

    def t_put_fact_wings():
        from nova import db

        db.put_fact("Tx-CLAW", "open-smoke", "body", kind="claw")
        db.put_fact("Ax-OPS", "open-smoke-ax", "body")
        con = db.connect()
        rows = con.execute(
            "SELECT whi FROM facts WHERE title LIKE 'open-smoke%' ORDER BY id"
        ).fetchall()
        con.close()
        wings = [r["whi"] for r in rows]
        assert "Tx-CLAW" in wings and "Ax-OPS" in wings, wings

    check("put_fact wings preserve", t_put_fact_wings)

    def t_clear_ingest_dry():
        from nova import office, db

        office._ensure()
        # seed a queued packet + waiting json
        office.post_packet(dest="brief@local", kind="ingest", body="smoke-wait")
        waiting = db.home() / "data" / "queue" / "waiting"
        waiting.mkdir(parents=True, exist_ok=True)
        (waiting / "smoke_job.json").write_text('{"id":"smoke"}\n', encoding="utf-8")
        res = office.clear_standing_ingest(dry_run=True, backup=False)
        assert res.get("ok") is True
        assert res.get("dry_run") is True
        assert int(res.get("packets") or 0) >= 1
        assert int(res.get("fs_waiting") or 0) >= 1
        # dry_run must not move file
        assert (waiting / "smoke_job.json").is_file()

    check("clear_standing_ingest dry-run", t_clear_ingest_dry)

    def t_automate_flag():
        from nova import office

        office.set_automate_queue(True)
        assert office.get_automate_queue() is True
        office.set_automate_queue(False)
        assert office.get_automate_queue() is False
        path = office.automate_queue_path()
        assert path.is_file()

    check("automate_queue persist", t_automate_flag)

    def t_forge_listing():
        from nova import forge

        names = [t["name"] for t in forge.FORGE]
        assert "ingest-clear-daily" in names, names

    check("forge ingest-clear-daily", t_forge_listing)

    def t_sched_key():
        from nova import sched

        # unknown still errors; known key present in source path via run_named
        src = Path(sched.__file__).read_text(encoding="utf-8")
        assert "ingest-clear-daily" in src

    check("sched knows ingest-clear-daily", t_sched_key)

    def t_web_uses_pipe():
        src = (ROOT / "nova" / "hands" / "web.py").read_text(encoding="utf-8")
        assert "ingest_pipe.store_accepted" in src
        assert "store: bool" in src or "store: bool =" in src or "*, store" in src

    check("web.fetch routes ingest_pipe", t_web_uses_pipe)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print("---")
    print(f"SUMMARY  PASS={passed}  FAIL={failed}  total={len(results)}")
    for name, ok, msg in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  ({msg})"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
