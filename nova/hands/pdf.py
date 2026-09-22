"""Text-layer PDF → Tx-PDF. Scanned pages stay a note."""

from __future__ import annotations

from pathlib import Path

from nova import db


def ingest(path: str) -> dict:
    p = Path(path).expanduser()
    if not p.is_file():
        return {"ok": False, "error": f"not a file {p}"}
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"ok": False, "error": "pip install pypdf"}
    try:
        reader = PdfReader(str(p))
        pages = []
        for i, page in enumerate(reader.pages[:40]):
            pages.append(page.extract_text() or "")
        text = "\n".join(pages).strip()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    dest = db.home() / "data" / "artifacts"
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / (p.stem + ".txt")
    out.write_text(text[:200000], encoding="utf-8")
    db.put_fact("Tx-PDF", p.name, text[:8000] or "(no text layer — scanned?)")
    return {"ok": True, "pages": min(40, len(reader.pages)), "chars": len(text), "path": str(out), "whi": "Tx-PDF"}
