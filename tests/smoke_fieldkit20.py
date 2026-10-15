#!/usr/bin/env python3
"""Fieldkit 2.0 smoke suite — run from fieldkit_v2_build with PYTHONPATH=."""
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

    # 1) Temp NOVA_HOME
    tmp = Path(tempfile.mkdtemp(prefix="nova_fk2_smoke_"))
    data = tmp / "data"
    data.mkdir(parents=True, exist_ok=True)
    os.environ["NOVA_HOME"] = str(tmp)
    print(f"NOVA_HOME={tmp}")

    def t_imports():
        import nova.db  # noqa: F401
        import nova.leash  # noqa: F401
        import nova.proof  # noqa: F401
        import nova.hearthbeat  # noqa: F401
        import nova.mail  # noqa: F401
        import nova.mail.tentacle_client  # noqa: F401
        import nova.ingest_pipe  # noqa: F401
        import nova.forge  # noqa: F401

    check("imports", t_imports)

    def t_put_fact_tx():
        from nova import db

        db.put_fact("Tx-CLAW", "proof-reject", "smoke", kind="claw")
        con = db.connect()
        row = con.execute(
            "SELECT whi, title FROM facts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        con.close()
        assert row is not None
        assert row["whi"] == "Tx-CLAW", row["whi"]
        assert row["title"] == "proof-reject"

    check("put_fact Tx-CLAW preserve", t_put_fact_tx)

    def t_put_fact_ax():
        from nova import db

        db.put_fact("Ax-CLAW", "ok", "smoke")
        con = db.connect()
        row = con.execute(
            "SELECT whi, title FROM facts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        con.close()
        assert row is not None
        assert row["whi"] == "Ax-CLAW", row["whi"]

    check("put_fact Ax-CLAW preserve", t_put_fact_ax)

    def t_forge_step():
        from nova.leash import forge_step

        outbox = tmp / "nova-out"
        outbox.mkdir(parents=True, exist_ok=True)
        artifact = outbox / "smoke_artifact.txt"
        artifact.write_text("fieldkit20-smoke-bytes\n", encoding="utf-8")
        step = tmp / "STEP_SMOKE.txt"
        step.write_text(
            "GOAL: smoke\nFILES: smoke_artifact.txt\nDONE when: proof\n",
            encoding="utf-8",
        )
        env = forge_step(step, outbox=outbox)
        assert env.get("kind") == "forge_step", env
        assert env.get("ok") is True, env
        assert int(env.get("bytes_total") or 0) > 0, env
        assert env.get("proof", {}).get("bytes_total", 0) > 0

    check("forge_step bytes_total", t_forge_step)

    def t_deck():
        deck = json.loads((ROOT / "nova" / "gui" / "deck.json").read_text(encoding="utf-8"))
        bad = {"ingest", "jobs", "status", "webgate"}
        for tile in deck.get("tiles") or []:
            if tile.get("id") in bad and tile.get("live") is True:
                raise AssertionError(f"alias {tile['id']} still live")

    check("deck aliases dead", t_deck)

    def t_version():
        ver = (ROOT / "VERSION").read_text(encoding="utf-8")
        if ver.startswith("\ufeff"):
            raise AssertionError("VERSION has BOM")
        assert ver.startswith("2.1.0"), ver[:40]  # 2.1: version bump

    check("VERSION 2.1.0", t_version)

    def t_mail_client():
        from nova.mail.tentacle_client import TentacleClient, default_client

        c = default_client()
        assert c.host == "192.0.2.10"
        assert c.node_id == "tentacle-01"
        assert c.display_name == "Tentacle-01"
        assert c.mail_address == "tentacle@tentacle-01"
        stub = c.poll_mail()
        assert stub.get("ok") is True
        assert stub.get("queued") == []
        assert TentacleClient is not None

    check("mail TentacleClient", t_mail_client)

    def t_forge_entry():
        from nova import forge

        names = [t["name"] for t in forge.FORGE]
        assert "leash-forge" in names, names

    check("forge leash-forge entry", t_forge_entry)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print("---")
    print(f"SUMMARY  PASS={passed}  FAIL={failed}  total={len(results)}")
    for name, ok, msg in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  ({msg})"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
