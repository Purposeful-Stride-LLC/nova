"""Watson — efficient Windows metal map (tree-like). Code only, no LLM.

Companion to Holmes probes: Holmes asks what the machine *is doing*;
Watson maps what is *there* under key roots (fieldkit, thumb, openclaw).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from nova.db import home, insert_obs, put_fact, zulu

SKIP_DIR = {
    "__pycache__", ".git", ".venv", "node_modules", ".tox", ".mypy_cache",
    "System Volume Information", "$RECYCLE.BIN", "Recovery",
}
SKIP_SUFFIX = {".pyc", ".pyo", ".swp", ".tmp"}

DEFAULT_ROOTS = [
    home(),
    Path(r"Documents\NOVA"),
    Path(r"D:\pg\ai"),
    Path.home() / ".openclaw" / "workspace",
]


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIR or name.startswith(".")


def tree_map(
    root: Path,
    *,
    max_depth: int = 3,
    max_entries: int = 400,
) -> dict:
    root = Path(root)
    if not root.exists():
        return {"root": str(root), "ok": False, "error": "missing"}
    entries = []
    file_n = dir_n = 0
    bytes_n = 0

    def walk(cur: Path, depth: int) -> None:
        nonlocal file_n, dir_n, bytes_n
        if len(entries) >= max_entries or depth > max_depth:
            return
        try:
            kids = sorted(cur.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            entries.append({"path": str(cur), "kind": "denied", "depth": depth})
            return
        for p in kids:
            if len(entries) >= max_entries:
                return
            if p.is_dir():
                if _should_skip_dir(p.name):
                    continue
                dir_n += 1
                entries.append({"path": str(p), "kind": "dir", "depth": depth})
                walk(p, depth + 1)
            else:
                if p.suffix.lower() in SKIP_SUFFIX:
                    continue
                try:
                    sz = p.stat().st_size
                except OSError:
                    sz = 0
                file_n += 1
                bytes_n += sz
                entries.append(
                    {
                        "path": str(p),
                        "kind": "file",
                        "depth": depth,
                        "bytes": sz,
                        "suffix": p.suffix.lower(),
                    }
                )

    walk(root if root.is_dir() else root.parent, 0 if root.is_dir() else 0)
    if root.is_file():
        entries = [{"path": str(root), "kind": "file", "depth": 0, "bytes": root.stat().st_size}]
        file_n, dir_n, bytes_n = 1, 0, entries[0]["bytes"]
    return {
        "root": str(root),
        "ok": True,
        "max_depth": max_depth,
        "files": file_n,
        "dirs": dir_n,
        "bytes": bytes_n,
        "truncated": len(entries) >= max_entries,
        "entries": entries,
    }


def map_metal(roots: list[Path] | None = None, max_depth: int = 3) -> dict:
    roots = roots or DEFAULT_ROOTS
    maps = []
    for r in roots:
        maps.append(tree_map(Path(r), max_depth=max_depth))
    out = {"zulu": zulu(), "ok": True, "maps": maps, "role": "watson"}
    # observations + fact (no LLM)
    insert_obs("watson", True, json.dumps({"zulu": out["zulu"], "n_roots": len(maps), "summary": [
        {"root": m.get("root"), "files": m.get("files"), "dirs": m.get("dirs"), "bytes": m.get("bytes"), "ok": m.get("ok")}
        for m in maps
    ]})[:4000])
    put_fact(
        "Ax-WATSON",
        "metal-map",
        json.dumps({
            "zulu": out["zulu"],
            "roots": [
                {"root": m.get("root"), "files": m.get("files"), "dirs": m.get("dirs"), "bytes": m.get("bytes"), "ok": m.get("ok"), "truncated": m.get("truncated")}
                for m in maps
            ],
        })[:4000],
        kind="crawl",
    )
    # also write a compact tree text artifact
    lines = [f"# Watson metal map {out['zulu']}", ""]
    for m in maps:
        lines.append(f"## {m.get('root')} ok={m.get('ok')} files={m.get('files')} dirs={m.get('dirs')}")
        for e in (m.get("entries") or [])[:80]:
            pad = "  " * int(e.get("depth") or 0)
            kind = e.get("kind")
            name = Path(e.get("path") or "").name
            if kind == "dir":
                lines.append(f"{pad}{name}/")
            elif kind == "file":
                lines.append(f"{pad}{name} ({e.get('bytes')})")
            else:
                lines.append(f"{pad}? {name}")
        lines.append("")
    dest = home() / "data" / "artifacts" / "watson_tree.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines), encoding="utf-8")
    out["artifact"] = str(dest)
    return out
