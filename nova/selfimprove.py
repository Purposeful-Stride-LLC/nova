"""Closed self-improvement loop (fieldkit 2.1), HIL at every gate:

  propose -> council review -> operator approve -> apply (sandbox/staged copy only)
          -> verify (tests) -> record PROOF

Nothing auto-promotes. Each stage is a file under <NOVA_HOME>/data/selfimprove/<pid>/ and a stage
refuses unless the previous one is complete:
  proposal.json   {title, why, files: {relpath: new_text}, tests: [pytest args]}
  reviews/*.json  {seat, verdict: agree|amend|oppose, notes}   (>= min_reviews, no 'oppose')
  approval.json   {by, ts}                                     (operator; via cmdinbox or CLI)
  apply.json      {target, files: {rel: {sha_before, sha_after}}}
  verify.json     {cmd, rc, summary}
  PROOF.json      {pid, sha256 of every file, tests rc, reviewers, approver}
apply() only writes into a target root that holds a `.nova_sandbox` marker file, never the
running live kit. Promotion of a verified sandbox to live is a separate, manual cutover.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

MIN_REVIEWS = 1
MARKER = ".nova_sandbox"


def _root() -> Path:
    from nova import db
    r = db.home() / "data" / "selfimprove"
    r.mkdir(parents=True, exist_ok=True)
    return r


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _w(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=True), encoding="utf-8")
    os.replace(tmp, p)


def _r(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _sha_text(s: str | bytes) -> str:
    return hashlib.sha256(s if isinstance(s, bytes) else s.encode("utf-8")).hexdigest()


def propose(title: str, why: str, files: dict[str, str], tests: list[str] | None = None, source: str = "operator") -> dict:
    for rel in files:
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            return {"ok": False, "error": f"path must be kit-relative: {rel}"}
    pid = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + "-" + _sha_text(title + why)[:6]
    _w(_root() / pid / "proposal.json", {"pid": pid, "title": title, "why": why, "files": files,
                                         "tests": tests or ["-q", "tests"], "source": source, "ts": _now()})
    return {"ok": True, "pid": pid, "stage": "proposed"}


def review(pid: str, seat: str, verdict: str, notes: str = "") -> dict:
    d = _root() / pid
    if not (d / "proposal.json").is_file():
        return {"ok": False, "error": "no proposal"}
    if verdict not in ("agree", "amend", "oppose"):
        return {"ok": False, "error": "verdict must be agree|amend|oppose"}
    _w(d / "reviews" / f"{seat}.json", {"seat": seat, "verdict": verdict, "notes": notes[:2000], "ts": _now()})
    return {"ok": True, "pid": pid, "seat": seat, "verdict": verdict}


def council_review(pid: str, ask, seats: tuple[str, ...] = ("reviewer",)) -> dict:
    """Ask council seat(s) through `ask(prompt)->str` (e.g. chamber.ask_brief, which must hold the GPU
    lock). The verdict is parsed from the first word; anything unparseable counts as 'amend'."""
    p = _r(_root() / pid / "proposal.json")
    out = {}
    for seat in seats:
        prompt = (f"Review this NOVA change. Reply with one word first: AGREE, AMEND or OPPOSE, then one risk.\n"
                  f"TITLE: {p['title']}\nWHY: {p['why']}\nFILES: {', '.join(p['files'])}")
        txt = (ask(prompt) or "").strip()
        head = txt.split()[0].strip(".:,").lower() if txt else ""
        verdict = head if head in ("agree", "amend", "oppose") else "amend"
        out[seat] = review(pid, seat, verdict, txt)
    return out


def status(pid: str) -> dict:
    d = _root() / pid
    revs = [_r(p) for p in sorted((d / "reviews").glob("*.json"))] if (d / "reviews").is_dir() else []
    st = {"pid": pid, "proposed": (d / "proposal.json").is_file(), "reviews": revs,
          "review_ok": len(revs) >= MIN_REVIEWS and not any(r["verdict"] == "oppose" for r in revs),
          "approved": (d / "approval.json").is_file(), "applied": (d / "apply.json").is_file(),
          "verified": (d / "verify.json").is_file() and _r(d / "verify.json").get("rc") == 0,
          "proof": (d / "PROOF.json").is_file()}
    return st


def approve(pid: str, by: str = "operator") -> dict:
    st = status(pid)
    if not st["proposed"]:
        return {"ok": False, "error": "no proposal"}
    if not st["review_ok"]:
        return {"ok": False, "refused": True, "error": f"council review missing or opposed (need >= {MIN_REVIEWS}, no oppose)"}
    _w(_root() / pid / "approval.json", {"by": by, "ts": _now()})
    return {"ok": True, "pid": pid, "stage": "approved"}


def apply(pid: str, target: str | Path | None = None, approved_cmd: str = "") -> dict:
    """Apply into a sandbox/staged copy only (target must contain .nova_sandbox)."""
    st = status(pid)
    if not st["approved"]:
        return {"ok": False, "refused": True, "error": "operator approval missing"}
    if not st["review_ok"]:
        return {"ok": False, "refused": True, "error": "review not ok"}
    tgt = Path(target or os.environ.get("NOVA_SANDBOX") or "")
    if not str(tgt) or not (tgt / MARKER).is_file():
        return {"ok": False, "refused": True, "error": f"target lacks {MARKER} marker (sandbox only)"}
    p = _r(_root() / pid / "proposal.json")
    rec = {"target_name": tgt.name, "files": {}, "ts": _now(), "cmd": approved_cmd}
    for rel, text in p["files"].items():
        f = tgt / rel
        before = _sha_text(f.read_bytes()) if f.is_file() else None
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        rec["files"][rel] = {"sha_before": before, "sha_after": _sha_text(f.read_bytes())}
    _w(_root() / pid / "apply.json", rec)
    return {"ok": True, "pid": pid, "stage": "applied", "files": list(rec["files"])}


def verify(pid: str, target: str | Path, env: dict | None = None, timeout: int = 600) -> dict:
    st = status(pid)
    if not st["applied"]:
        return {"ok": False, "error": "not applied"}
    p = _r(_root() / pid / "proposal.json")
    cmd = [sys.executable, "-m", "pytest", *p["tests"]]
    e = {**os.environ, **(env or {})}
    r = subprocess.run(cmd, cwd=str(target), env=e, capture_output=True, text=True, timeout=timeout)
    tail = (r.stdout or "").strip().splitlines()[-1:] or [""]
    _w(_root() / pid / "verify.json", {"cmd": " ".join(cmd[1:]), "rc": r.returncode, "summary": tail[0][:300], "ts": _now()})
    return {"ok": r.returncode == 0, "rc": r.returncode, "summary": tail[0]}


def record_proof(pid: str, target: str | Path) -> dict:
    st = status(pid)
    if not st["verified"]:
        return {"ok": False, "refused": True, "error": "tests not passing; no PROOF"}
    d = _root() / pid
    ap = _r(d / "apply.json")
    shas = {rel: _sha_text((Path(target) / rel).read_bytes()) for rel in ap["files"]}
    match = all(shas[rel] == v["sha_after"] for rel, v in ap["files"].items())
    proof = {"pid": pid, "files_sha256": shas, "match_apply": match, "verify": _r(d / "verify.json"),
             "reviewers": [r["seat"] + ":" + r["verdict"] for r in st["reviews"]],
             "approved_by": _r(d / "approval.json")["by"], "ts": _now(),
             "line": f"PROOF: files={len(shas)} tests_rc={_r(d / 'verify.json')['rc']} match={match}"}
    _w(d / "PROOF.json", proof)
    try:
        from nova import db
        db.log("selfimprove", proof["ts"], proof["ts"], 0, "" if match else "sha_mismatch", f"{pid} {proof['line']}")
    except Exception:
        pass
    return {"ok": match, **proof}
