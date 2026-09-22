"""NOVA ingest pipe: fetch/crawl -> matrix weigh -> optional LLM summary -> palace.

Provenance on every accepted store (in body header + Ax/0x fact):
  source_url, accessed (zulu), llm, mask, matrix_score, whi
"""
from __future__ import annotations

import json
import hashlib
from typing import Any

from nova import db, matrix, whi, masks

DEFAULT_SUMMARY_MODEL = "qwen3:8b"
DEFAULT_SUMMARY_MASK = "chronicler"
# Investigation masks preferred for research summaries
ANALYSIS_MASKS = ("scout", "analyst", "skeptic", "synthesist", "chronicler")


def _header(**kv: Any) -> str:
    lines = []
    for k, v in kv.items():
        if v is None or v == "":
            continue
        lines.append(f"{k}={v}")
    return "\n".join(lines)


def weigh_text(text: str, html_len: int = 0) -> dict:
    return matrix.analyze(text or "", html_len=html_len)


def summarize(
    text: str,
    *,
    title: str = "",
    url: str = "",
    model: str = DEFAULT_SUMMARY_MODEL,
    mask: str = DEFAULT_SUMMARY_MASK,
) -> dict:
    """LLM summary under a mask. Returns {ok, summary, model, mask, error?}."""
    from nova import ollama_talk

    mask_key = (mask or DEFAULT_SUMMARY_MASK).strip().lower()
    if mask_key not in masks.MASK_SPECS:
        mask_key = DEFAULT_SUMMARY_MASK
    sys = masks.apply(mask_key)
    prompt = (
        f"{sys}\n\nSOURCE_URL: {url}\nTITLE: {title}\n"
        "TASK: Summarize for the memory palace. Keep facts, numbers, named systems. "
        "Max 12 lines. Stamp WHI wing guess (Ax/Tx/0x) on first line as WHI: ...\n\n"
        f"TEXT:\n{(text or '')[:6000]}"
    )
    try:
        reply = ollama_talk.chat(model, prompt[:7000], timeout=180)
        summary = (reply or "").strip()[:4000]
        return {"ok": bool(summary), "summary": summary, "model": model, "mask": mask_key}
    except Exception as exc:
        return {"ok": False, "summary": "", "model": model, "mask": mask_key, "error": str(exc)}


def store_accepted(
    *,
    title: str,
    url: str,
    raw_text: str,
    matrix_row: dict,
    summary: str,
    model: str,
    mask: str,
    whi_code: str | None = None,
    status: str = "live",
) -> dict:
    """Write live chunk + 0x/Ax fact with full provenance header."""
    accessed = db.zulu()
    mscore = matrix_row.get("score")
    mhash = matrix_row.get("hash") or hashlib.sha256((raw_text or "").encode()).hexdigest()[:16]
    wing = (whi_code or "").strip()
    if not wing:
        wing = whi.classify(summary or raw_text, title=title, url=url, kind="web", default="0x-WEB")
    if not wing.startswith(("Ax-", "Tx-", "0x-")):
        wing = "0x-WEB"
    head = _header(
        source_url=url,
        accessed=accessed,
        llm=model,
        mask=mask,
        matrix_score=mscore,
        content_hash=mhash,
        whi=wing,
        title=title,
    )
    body = f"{head}\n\n{(summary or raw_text)[:7500]}"
    cite = f"web:{mhash}:{url}"[:240]
    con = db.connect()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS chunks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          zulu TEXT NOT NULL,
          whi TEXT NOT NULL,
          source_cite TEXT NOT NULL,
          text TEXT NOT NULL,
          hash TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'temp'
        );"""
    )
    con.execute(
        "INSERT INTO chunks(zulu,whi,source_cite,text,hash,status) VALUES (?,?,?,?,?,?)",
        (accessed, wing, cite, body[:8000], mhash, status),
    )
    con.commit()
    cid = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
    con.close()
    db.put_fact(
        wing,
        (title or url)[:160],
        body[:8000],
        source_url=url,
        content_hash=mhash,
        matrix_json=matrix.dump(matrix_row),
        kind="web",
    )
    return {"ok": True, "chunk_id": cid, "whi": wing, "accessed": accessed, "cite": cite, "matrix_score": mscore, "llm": model, "mask": mask}


def process_url(
    url: str,
    *,
    model: str = DEFAULT_SUMMARY_MODEL,
    mask: str = DEFAULT_SUMMARY_MASK,
    summarize_ok: bool = True,
    min_score: int = 28,
) -> dict:
    """Full pipe using hands.web fetch + matrix + optional summary store."""
    from nova.hands import web as web_hand

    got = web_hand.fetch(url)
    if not got.get("ok"):
        return {"ok": False, "error": got.get("error"), "url": url}
    m = got.get("matrix") or {}
    title = got.get("title") or url
    final = got.get("url") or url
    # Re-read text from artifact for summary body
    path = got.get("path")
    text = ""
    if path:
        try:
            from pathlib import Path
            raw = Path(path).read_text(encoding="utf-8", errors="replace")
            # file is final\nmatrix\n\ntext
            parts = raw.split("\n\n", 1)
            text = parts[1] if len(parts) > 1 else raw
        except Exception:
            text = ""
    if not got.get("ingested"):
        return {
            "ok": True,
            "ingested": False,
            "url": final,
            "title": title,
            "matrix": m,
            "reason": m.get("label") or "reject-thin",
        }
    # strengthen gate with min_score
    if int(m.get("score") or 0) < min_score:
        db.put_fact(
            "Tx-REJECT",
            f"score-low:{title}"[:160],
            f"reason=score-low\nurl={final}\nscore={m.get('score')}\n",
            source_url=final,
            content_hash=m.get("hash"),
            matrix_json=matrix.dump(m),
            reason="score-low",
        )
        return {"ok": True, "ingested": False, "url": final, "matrix": m, "reason": "score-low"}

    summary = ""
    model_used = model
    mask_used = mask
    if summarize_ok:
        s = summarize(text, title=title, url=final, model=model, mask=mask)
        if s.get("ok"):
            summary = s["summary"]
            model_used = s["model"]
            mask_used = s["mask"]
        else:
            # fall back to truncated raw with provenance noting summary-fail
            summary = f"WHI: 0x-WEB\n(summary-fail: {s.get('error')})\n\n{(text or '')[:2000]}"
            mask_used = mask
    else:
        summary = (text or "")[:2000]

    stored = store_accepted(
        title=title,
        url=final,
        raw_text=text,
        matrix_row=m,
        summary=summary,
        model=model_used,
        mask=mask_used,
        status="live",
    )
    return {"ok": True, "ingested": True, **stored, "matrix": m, "title": title, "url": final}


def process_crawl_chunk(
    chunk_id: int,
    *,
    model: str = DEFAULT_SUMMARY_MODEL,
    mask: str = DEFAULT_SUMMARY_MASK,
    min_score: int = 28,
) -> dict:
    """Weigh a crawl temp chunk; promote to live with LLM summary + provenance or clear."""
    con = db.connect()
    row = con.execute("SELECT * FROM chunks WHERE id=?", (chunk_id,)).fetchone()
    con.close()
    if not row:
        return {"ok": False, "error": "missing chunk"}
    raw = row["text"] or ""
    url = ""
    title = ""
    body = raw
    for line in raw.splitlines()[:8]:
        if line.startswith("url="):
            url = line[4:].strip()
        elif line.startswith("title="):
            title = line[6:].strip()
    if "\n\n" in raw:
        body = raw.split("\n\n", 1)[1]
    m = weigh_text(body)
    if m.get("label") != "ingest" or int(m.get("score") or 0) < min_score:
        con = db.connect()
        con.execute("UPDATE chunks SET status='cleared', whi=? WHERE id=?", ("Tx-REJECT", chunk_id))
        con.commit()
        con.close()
        db.put_fact(
            "Tx-REJECT",
            f"crawl-thin:{title or chunk_id}"[:160],
            f"reason={m.get('label')}\nurl={url}\nscore={m.get('score')}\nchunk={chunk_id}\n",
            source_url=url,
            content_hash=m.get("hash"),
            matrix_json=matrix.dump(m),
            reason=m.get("label"),
        )
        return {"ok": True, "ingested": False, "chunk_id": chunk_id, "matrix": m, "reason": m.get("label")}

    s = summarize(body, title=title, url=url, model=model, mask=mask)
    summary = s.get("summary") if s.get("ok") else f"(summary-fail)\n{body[:1500]}"
    accessed = db.zulu()
    wing = whi.classify(summary or body, title=title, url=url, kind="web", default="0x-WEB")
    head = _header(
        source_url=url,
        accessed=accessed,
        llm=s.get("model") or model,
        mask=s.get("mask") or mask,
        matrix_score=m.get("score"),
        content_hash=m.get("hash"),
        whi=wing,
        title=title,
        crawl_chunk=chunk_id,
    )
    text_out = f"{head}\n\n{(summary or '')[:7500]}"
    con = db.connect()
    con.execute(
        "UPDATE chunks SET status='live', whi=?, text=?, zulu=? WHERE id=?",
        (wing, text_out[:8000], accessed, chunk_id),
    )
    con.commit()
    con.close()
    db.put_fact(
        wing,
        (title or url or f"chunk/{chunk_id}")[:160],
        text_out[:8000],
        source_url=url,
        content_hash=m.get("hash"),
        matrix_json=matrix.dump(m),
        kind="web",
    )
    return {
        "ok": True,
        "ingested": True,
        "chunk_id": chunk_id,
        "whi": wing,
        "matrix": m,
        "llm": s.get("model") or model,
        "mask": s.get("mask") or mask,
        "accessed": accessed,
    }
