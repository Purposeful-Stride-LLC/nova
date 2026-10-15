"""Disk retention (fieldkit 2.1): CONFIG + DRY-RUN REPORT ONLY. This module never deletes.

Config: <NOVA_HOME>/data/config/retention.json (DEFAULTS below). `dry_run_report()` lists what a
future, operator-approved trim WOULD remove, with sizes, and writes data/run/disk_dryrun.json.
`proposed_trims(parent)` extends that to sibling installs / zips / temp sandboxes (listing only).
CLI: python -m nova.disk report [--root KITROOT] [--parent NOVA_PARENT] [--temp TEMPDIR]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

DEFAULTS = {
    "stills": {"dir": "data/artifacts/vision", "glob": "*.jpg", "keep_days": 7, "keep_max": 200},
    "db_backups": {"globs": ["data/NOVA.db.bak-*"], "keep": 1},
    "old_dbs": {"globs": ["data/oldnova.db", "data/oldnova.db.zip"]},
    "tts_play_dupes": {"dir": "data/artifacts", "glob": "tts_*_play.wav", "verify_hash": True},
    "logs": {"files": ["data/master.log", "data/governor/governor_dryrun.jsonl"], "max_mb": 5},
    "apply_enabled": False,  # 2.1 ships report-only; apply needs Michael's approval and a later build
}


def _cfg(home: Path) -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))
    p = home / "data" / "config" / "retention.json"
    try:
        if p.is_file():
            for k, v in json.loads(p.read_text(encoding="utf-8")).items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
    except Exception as exc:
        cfg["_config_error"] = str(exc)[:120]
    return cfg


def _size(p: Path) -> int:
    try:
        if p.is_file():
            return p.stat().st_size
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    except OSError:
        return 0


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _mb(n: int) -> float:
    return round(n / 1e6, 2)


def dry_run_report(home: Path | None = None, write: bool = True, now: float | None = None) -> dict:
    if home is None:
        from nova import db
        home = db.home()
    home = Path(home)
    now = now or time.time()
    cfg = _cfg(home)
    items: list[dict] = []
    # stills: keep newest keep_max AND anything younger than keep_days
    sc = cfg["stills"]
    d = home / sc["dir"]
    stills = sorted(d.glob(sc["glob"]), key=lambda p: p.stat().st_mtime, reverse=True) if d.is_dir() else []
    old = [p for i, p in enumerate(stills) if i >= sc["keep_max"] and (now - p.stat().st_mtime) > sc["keep_days"] * 86400]
    items.append({"rule": "stills", "count": len(old), "of": len(stills), "bytes": sum(p.stat().st_size for p in old),
                  "keep": f"newest {sc['keep_max']} or < {sc['keep_days']} d"})
    # db backups beyond keep
    bk = []
    for g in cfg["db_backups"]["globs"]:
        bk += list(home.glob(g))
    bk.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    drop = bk[cfg["db_backups"]["keep"]:]
    items.append({"rule": "db_backups", "count": len(drop), "of": len(bk), "bytes": sum(_size(p) for p in drop),
                  "files": [p.name for p in drop], "keep": f"newest {cfg['db_backups']['keep']}"})
    od = []
    for g in cfg["old_dbs"]["globs"]:
        od += list(home.glob(g))
    items.append({"rule": "old_dbs", "count": len(od), "bytes": sum(_size(p) for p in od), "files": [p.name for p in od]})
    # _play.wav duplicates, hash-verified
    tc = cfg["tts_play_dupes"]
    dup, unverified = [], []
    for p in (home / tc["dir"]).rglob(tc["glob"]) if (home / tc["dir"]).is_dir() else []:
        twin = p.with_name(p.name.replace("_play.wav", ".wav"))
        if twin.is_file() and twin.stat().st_size == p.stat().st_size:
            if not tc.get("verify_hash") or _sha(twin) == _sha(p):
                dup.append(p)
            else:
                unverified.append(p.name)
    items.append({"rule": "tts_play_dupes", "count": len(dup), "bytes": sum(p.stat().st_size for p in dup),
                  "hash_verified": bool(tc.get("verify_hash")), "differs": unverified})
    # logs over max_mb -> rotate (would keep the newest max_mb)
    lg = cfg["logs"]
    for f in lg["files"]:
        p = home / f
        if p.is_file() and p.stat().st_size > lg["max_mb"] * 1e6:
            items.append({"rule": "log_rotate", "file": f, "count": 1, "bytes": int(p.stat().st_size - lg["max_mb"] * 1e6)})
    total = sum(i["bytes"] for i in items)
    rep = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mode": "dry-run (no deletes)",
           "apply_enabled": False, "items": items, "total_bytes": total, "total_mb": _mb(total)}
    if write:
        try:
            out = home / "data" / "run" / "disk_dryrun.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
        except OSError:
            pass
    return rep


def proposed_trims(kit: Path, parent: Path | None = None, temp: Path | None = None) -> dict:
    """Listing only: kit-internal dry-run + sibling clutter + temp sandboxes. Sizes in bytes."""
    rep = dry_run_report(kit, write=False)
    extra = []
    parent = parent or kit.parent
    for name in ("NOVA_fieldkit_v1_4", "STAGING", "NOVA_fieldkit_v2_0.zip", "_fk2_stage.zip",
                 "_nova_public_sync_20260926", "_nova_public_sync_20260926.zip", "_export_nova_clean",
                 "_export_nova_clean.tar", "_export_AiTutor.tar", "NOVA_fieldkit_mirror_sans_db.zip"):
        p = parent / name
        if p.exists():
            extra.append({"rule": "sibling", "path": name, "bytes": _size(p)})
    if temp and temp.is_dir():
        for p in sorted(temp.glob("nova_sim_*")) + sorted(temp.glob("nr*")) + sorted(temp.glob("v21_*.zip")):
            extra.append({"rule": "temp_sandbox", "path": p.name, "bytes": _size(p)})
    total = rep["total_bytes"] + sum(e["bytes"] for e in extra)
    return {"kit": rep, "extra": extra, "total_bytes": total, "total_mb": _mb(total)}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m nova.disk")
    ap.add_argument("cmd", choices=["report", "trims"])
    ap.add_argument("--root", default=None)
    ap.add_argument("--parent", default=None)
    ap.add_argument("--temp", default=None)
    a = ap.parse_args(argv)
    if a.cmd == "report":
        print(json.dumps(dry_run_report(Path(a.root) if a.root else None, write=a.root is None), indent=1))
    else:
        if not a.root:
            print("--root required", file=sys.stderr)
            return 2
        print(json.dumps(proposed_trims(Path(a.root), Path(a.parent) if a.parent else None,
                                        Path(a.temp) if a.temp else None), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
