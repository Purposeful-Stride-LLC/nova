"""One-off file/folder inspection. Facts first, then optional expert opinions."""

from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path

SKIP = {".pyc", ".db", ".wav", ".jpg", ".jpeg", ".png", ".zip"}


def kind(p: Path) -> str:
    if p.is_dir():
        return "dir"
    suf = p.suffix.lower()
    if suf in {".py"}:
        return "python"
    if suf in {".txt", ".md"}:
        return "text"
    if suf in {".pdf"}:
        return "pdf"
    if suf in {".json"}:
        return "json"
    if suf in {".html", ".htm"}:
        return "html"
    guess, _ = mimetypes.guess_type(str(p))
    return guess or suf or "bin"


def facts(p: Path) -> dict:
    st = p.stat()
    rec = {
        "path": str(p.resolve()),
        "kind": kind(p),
        "bytes": st.st_size,
        "mtime": int(st.st_mtime),
    }
    if p.is_file() and p.suffix.lower() not in SKIP and st.st_size < 400_000:
        data = p.read_bytes()
        rec["sha256"] = hashlib.sha256(data).hexdigest()[:16]
        if rec["kind"] in {"python", "text", "json"}:
            try:
                text = data.decode("utf-8", "replace")
            except Exception:
                text = ""
            rec["lines"] = text.count("\n") + 1
            rec["head"] = text[:240]
    if p.is_dir():
        kids = [c.name for c in p.iterdir()]
        rec["children"] = len(kids)
        rec["sample"] = kids[:12]
    return rec


def walk(root: str, cap: int = 80) -> list[dict]:
    r = Path(root)
    out = [facts(r)]
    if r.is_dir():
        for c in sorted(r.rglob("*")):
            if c.suffix == ".pyc" or "__pycache__" in c.parts:
                continue
            out.append(facts(c))
            if len(out) >= cap:
                break
    return out


def mermaid(rows: list[dict]) -> str:
    lines = ["flowchart TD", "  A[path] --> B[kind]", "  B --> C[facts hash size lines]", "  C --> D[optional 0.5b clerk]", "  D --> E[optional 8b reviewer]", "  E --> F[report Tx-DEV]"]
    return "\n".join(lines)


def run(root: str, opinions: bool = False) -> dict:
    rows = walk(root)
    report = {
        "root": root,
        "n": len(rows),
        "kinds": {},
        "rows": rows,
        "mermaid": mermaid(rows),
    }
    for r in rows:
        report["kinds"][r["kind"]] = report["kinds"].get(r["kind"], 0) + 1
    dest = Path(__file__).resolve().parent.parent / "data" / "artifacts"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "sherlock.json"
    path.write_text(json.dumps(report, indent=2)[:80_000], encoding="utf-8")
    report["path"] = str(path)
    return report


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "nova"
    print(json.dumps({k: run(target)[k] for k in ("root", "n", "kinds", "path", "mermaid")}, indent=2))
