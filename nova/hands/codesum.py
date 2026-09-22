"""Windows-safe code/folder sum. Lands in Tx-CODE until promoted."""

from __future__ import annotations

from pathlib import Path

from nova import db, ollama_talk
from nova.masks import apply

EXTS = {".py", ".js", ".ts", ".go", ".rs", ".cpp", ".c", ".h", ".cs", ".java", ".sh", ".ps1", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"}
SKIP = {"__pycache__", ".git", ".venv", "node_modules"}
G = "\033[32m"
C = "\033[36m"
Y = "\033[33m"
X = "\033[0m"


def inventory(root: Path, cap: int = 40) -> list[Path]:
    if root.is_file():
        return [root]
    out = []
    for p in sorted(root.rglob("*")):
        if any(part in SKIP for part in p.parts):
            continue
        if p.is_file() and p.suffix.lower() in EXTS and p.stat().st_size < 400_000:
            out.append(p)
        if len(out) >= cap:
            break
    return out


def run(target: str, model: str) -> dict:
    root = Path(target).expanduser().resolve()
    if not root.exists():
        return {"ok": False, "error": f"missing {root}"}
    files = inventory(root)
    dest = db.home() / "data" / "artifacts"
    dest.mkdir(parents=True, exist_ok=True)
    bits = [f"# codesum {root}\n"]
    kind = "folder" if root.is_dir() else "file"
    prompt_folder = (
        apply("reviewer")
        + "\nThis is one file in a folder inventory. "
        "STRUCTURE / PURPOSE / KEY OPERATIONS / I/O / DEPENDENCIES. Tight.\n"
    )
    prompt_file = apply("reviewer") + "\nSingle program. Same headings. Note writes/reads.\n"
    head = prompt_folder if kind == "folder" else prompt_file
    lines_out = []
    for i, path in enumerate(files, 1):
        rel = str(path)
        print(f"{C}{i:3}{X} {path.name:<40} {Y}processing{X}")
        text = path.read_text(encoding="utf-8", errors="replace")[:6000]
        reply = ollama_talk.chat(model, head + f"FILE: {rel}\nCODE:\n{text}")
        bits.append(f"## {rel}\n{reply}\n")
        db.put_fact("Tx-CODE", path.name, reply[:2000])
        lines_out.append(f"{G}{i:3} done{X} {rel}")
        print(f"{G}{i:3} done{X} {path.name}")
    out = dest / "codesum.md"
    out.write_text("\n".join(bits), encoding="utf-8")
    db.put_fact("Tx-CODE", f"sum-{root.name}", f"{kind} {len(files)} files → {out}")
    return {"ok": True, "kind": kind, "files": len(files), "path": str(out)}
