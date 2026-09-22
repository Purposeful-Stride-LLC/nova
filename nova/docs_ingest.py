"""Documents -> WHI palace ingest (intentional feed; not thumb legacy)."""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from nova import db, ingest_pipe, whi

DOCS_ROOT = Path(r"C:\Users\wuchy\Documents")
NOVA_DOCS = DOCS_ROOT / "NOVA"
DAY1 = [
    DOCS_ROOT / "NOVA_Technology_Proposal_Purposeful_Strides_LLC_2026-08-06.docx",
    DOCS_ROOT / "NOVA_Field_Worker_Platform_BPC_Concept_Spec_Purposeful_Stride_LLC.docx",
    NOVA_DOCS / "clawbotinstructions.txt",
    NOVA_DOCS / "claw_coding_playbook.txt",
    NOVA_DOCS / "_scratch_projectnova_odt.txt",
]

DAY2 = [
    DOCS_ROOT / "Provisional_Patent_FrostShield_PurposefulStride_LLC.docx",
    DOCS_ROOT / "IP_Assignment_Lunar_Regolith_Ice_Harvesting_Microwave_Pyramid_System.pdf",
    DOCS_ROOT / "Operating_Concept_Hybrid_Energy_Station_Laboratory.docx",
    DOCS_ROOT / "Hammerhead_Spaceplane_Technical_Proposal_Purposeful_Stride_LLC.pdf",
]
DAY3 = [
    DOCS_ROOT / "Purposeful_Stride_LLC_IP_RD_Portfolio_Wuchevich.pdf",
    DOCS_ROOT / "IP_Assignment_Wuchevich_to_Purposeful_Stride_LLC_REFINED.docx",
    DOCS_ROOT / "Invention_Disclosure_Liquid_Metal_MHD_ReEntry_System.docx",
]

SECTION = 3500
OVERLAP = 200


def _ensure_queue(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS docs_queue (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          path TEXT NOT NULL UNIQUE,
          hash TEXT,
          status TEXT NOT NULL DEFAULT 'queued',
          zulu TEXT,
          last_err TEXT,
          note TEXT
        )
        """
    )
    con.commit()


def extract_text(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "error": f"missing {path}"}
    suf = path.suffix.lower()
    try:
        if suf in (".txt", ".md", ".csv", ".log", ".ai"):
            text = path.read_text(encoding="utf-8", errors="replace")
        elif suf == ".docx":
            from docx import Document

            doc = Document(str(path))
            text = "\n".join(p.text for p in doc.paragraphs if (p.text or "").strip())
        elif suf == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages[:60])
        else:
            return {"ok": False, "error": f"unsupported {suf}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    text = (text or "").strip()
    h = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
    return {"ok": True, "text": text, "chars": len(text), "hash": h, "title": path.stem}


def split_sections(text: str, size: int = SECTION, overlap: int = OVERLAP) -> list[str]:
    text = text or ""
    if len(text) <= size:
        return [text] if text else []
    out: list[str] = []
    i = 0
    while i < len(text):
        out.append(text[i : i + size])
        i += max(1, size - overlap)
        if len(out) >= 12:
            break
    return out


def scout(paths: list[Path] | None = None) -> dict[str, Any]:
    paths = paths or list(DAY1)
    con = db.connect()
    _ensure_queue(con)
    n = 0
    for p in paths:
        p = Path(p)
        if not p.is_file():
            continue
        raw = p.read_bytes()
        h = hashlib.sha256(raw).hexdigest()[:16]
        z = db.zulu()
        row = con.execute("SELECT id, hash, status FROM docs_queue WHERE path=?", (str(p),)).fetchone()
        if row and row["hash"] == h and row["status"] == "done":
            continue
        if row:
            con.execute(
                "UPDATE docs_queue SET hash=?, status='queued', zulu=?, last_err=NULL WHERE id=?",
                (h, z, row["id"]),
            )
        else:
            con.execute(
                "INSERT INTO docs_queue(path, hash, status, zulu) VALUES (?,?,?,?)",
                (str(p), h, "queued", z),
            )
        n += 1
    con.commit()
    return {"ok": True, "enqueued_or_refreshed": n}


def ingest_one(
    path: str | Path,
    *,
    model: str = "qwen2:0.5b",
    mask: str = "chronicler",
    min_score: int = 8,
    summarize_ok: bool = True,
) -> dict[str, Any]:
    p = Path(path)
    ex = extract_text(p)
    if not ex.get("ok"):
        return ex
    text = ex["text"]
    title = ex["title"]
    file_url = p.resolve().as_uri()
    sections = split_sections(text)
    results = []
    for i, sec in enumerate(sections):
        matrix_row = ingest_pipe.weigh_text(sec)
        score = int(matrix_row.get("score") or 0)
        if score < min_score and len(sec) < 400:
            results.append({"section": i, "skipped": True, "score": score})
            continue
        summary = ""
        if summarize_ok and len(sec) > 500:
            try:
                sm = ingest_pipe.summarize(sec, title=title, url=file_url, model=model, mask=mask)
                if isinstance(sm, dict):
                    summary = (sm.get("summary") or "") if sm.get("ok") else f"(summary failed: {sm.get('error')})"
                else:
                    summary = str(sm or "")
            except Exception as exc:
                summary = f"(summary failed: {exc})"
        if not summary:
            summary = sec[:2000]
        sec_title = title if len(sections) == 1 else f"{title} [{i+1}/{len(sections)}]"
        wing = whi.classify(summary, title=sec_title, url=file_url, kind="doc", default="0x-DOC")
        # Local Documents feed: keep palace wing stable for RAG
        if file_url.startswith("file:"):
            wing = "0x-DOC"
        elif not str(wing).startswith(("Ax-", "Tx-", "0x-")):
            wing = "0x-DOC"
        stored = ingest_pipe.store_accepted(
            title=sec_title,
            url=file_url,
            raw_text=sec,
            matrix_row=matrix_row,
            summary=summary,
            model=model,
            mask=mask,
            whi_code=wing,
            status="live",
        )
        results.append({"section": i, "score": score, "whi": wing, "stored": stored})
    con = db.connect()
    _ensure_queue(con)
    con.execute(
        "UPDATE docs_queue SET status=?, zulu=?, note=? WHERE path=?",
        ("done", db.zulu(), f"sections={len(results)}", str(p)),
    )
    con.commit()
    return {"ok": True, "path": str(p), "chars": ex["chars"], "sections": len(sections), "results": results}


def ingest_due(limit: int = 1, **kw: Any) -> dict[str, Any]:
    con = db.connect()
    _ensure_queue(con)
    rows = con.execute(
        "SELECT path FROM docs_queue WHERE status='queued' ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()
    out = []
    for r in rows:
        con.execute("UPDATE docs_queue SET status='running' WHERE path=?", (r["path"],))
        con.commit()
        try:
            out.append(ingest_one(r["path"], **kw))
        except Exception as exc:
            con.execute(
                "UPDATE docs_queue SET status='queued', last_err=? WHERE path=?",
                (str(exc)[:500], r["path"]),
            )
            con.commit()
            out.append({"ok": False, "path": r["path"], "error": str(exc)})
    return {"ok": True, "n": len(out), "items": out}


def day1_run() -> dict[str, Any]:
    scout(list(DAY1))
    items = []
    for p in DAY1:
        if p.is_file():
            items.append(ingest_one(p, model="qwen2:0.5b", mask="chronicler", min_score=8))
    return {"ok": True, "n": len(items), "items": items}

def run_days(days: list[int] | None = None, **kw) -> dict[str, Any]:
    days = days or [1, 2, 3]
    mapping = {1: DAY1, 2: DAY2, 3: DAY3}
    paths: list[Path] = []
    for d in days:
        paths.extend(mapping.get(int(d), []))
    scout(paths)
    items = []
    for p in paths:
        if p.is_file():
            items.append(ingest_one(p, **kw))
        else:
            items.append({"ok": False, "path": str(p), "error": "missing"})
    return {"ok": True, "n": len(items), "items": items}
