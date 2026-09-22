"""Aurelius / OpenClaw PROOF-before-DONE gate.

Ack is not proof. A STEP is only accepted when nova-out files exist and
each claimed PROOF: bytes=<n> matches the real file size.
"""
from __future__ import annotations

import re
from pathlib import Path

NOVA_OUT = Path.home() / ".openclaw" / "workspace" / "nova-out"
PROOF_RE = re.compile(r"PROOF:\s*bytes\s*=\s*(\d+)", re.I)
DONE_RE = re.compile(r"\bDONE\b", re.I)


def check_text(text: str, *, out_dir: Path | None = None) -> dict:
    out_dir = out_dir or NOVA_OUT
    text = text or ""
    claims = PROOF_RE.findall(text)
    if DONE_RE.search(text) and not claims:
        return {
            "ok": False,
            "accepted": False,
            "reason": "DONE without PROOF: bytes=<n>",
            "proofs": [],
        }
    proofs = []
    ok_all = True
    for n in claims:
        want = int(n)
        matched = None
        if out_dir.exists():
            for p in sorted(out_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if p.is_file() and p.stat().st_size == want:
                    matched = str(p)
                    break
        entry = {"bytes": want, "matched": matched, "ok": matched is not None}
        if matched is None:
            ok_all = False
        proofs.append(entry)
    if claims and not ok_all:
        return {"ok": False, "accepted": False, "reason": "PROOF bytes mismatch", "proofs": proofs}
    if claims and ok_all:
        return {"ok": True, "accepted": True, "reason": "PROOF matched", "proofs": proofs}
    return {"ok": True, "accepted": None, "reason": "no DONE/PROOF gate triggered", "proofs": []}


def enforce_on_reply(text: str) -> dict:
    from nova import db

    gate = check_text(text)
    if gate.get("accepted") is False:
        db.put_fact(
            "Tx-CLAW",
            "proof-reject",
            "reason=%s\n\n%s" % (gate.get("reason"), (text or "")[:1500]),
            kind="claw",
        )
    elif gate.get("accepted") is True:
        db.put_fact(
            "Ax-CLAW",
            "proof-accept",
            "proofs=%s\n\n%s" % (gate.get("proofs"), (text or "")[:800]),
            kind="claw",
        )
    return gate
