"""Fetch → strip → matrix → quality gate → WHI cite."""

from __future__ import annotations

import ssl
import urllib.request

from nova import db
from nova.matrix import analyze, dump, strip_html, page_title

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def _ctx():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch(url: str, cap: int = 120_000, *, store: bool = True) -> dict:
    """Fetch → strip → matrix → quality gate.

    When store=True (default), accepted pages go through ingest_pipe.store_accepted
    (chunks + force_class provenance). Rejects still stamp Tx-REJECT via put_fact.
    Pass store=False for callers (e.g. ingest_pipe.process_url) that store themselves.
    """
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "http(s) only"}
    from nova import gates  # 2.1: Brutus-style scope; unknown host -> refuse
    g = gates.host_allowed(url)
    if not g["allow"]:
        return {"ok": False, "refused": True, "error": g["reason"], "host": g.get("host")}
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25, context=_ctx()) as r:
            raw = r.read(cap)
            final = r.geturl()
            ctype = r.headers.get("Content-Type", "")
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    html = raw.decode("utf-8", "replace")
    title = page_title(html) or final
    text = strip_html(html)
    matrix = analyze(text, html_len=len(html))
    dest = db.home() / "data" / "artifacts" / "web_last.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"{final}\n{dump(matrix)}\n\n{text[:20000]}", encoding="utf-8")
    if matrix["label"] != "ingest":
        if store:
            reject_body = (
                f"reason={matrix['label']}\nurl={final}\nscore={matrix.get('score')}\n"
                f"chars={matrix.get('chars')}\n\n{(text or '')[:1200]}"
            )
            db.put_fact(
                "Tx-REJECT",
                f"{matrix['label']}:{title}"[:160],
                reject_body,
                source_url=final,
                content_hash=matrix["hash"],
                matrix_json=dump(matrix),
                reason=matrix["label"],
            )
        return {"ok": True, "ingested": False, "url": final, "matrix": matrix, "path": str(dest), "title": title}
    stored = None
    if store:
        from nova import ingest_pipe

        stored = ingest_pipe.store_accepted(
            title=title,
            url=final,
            raw_text=text,
            matrix_row=matrix,
            summary=(text or "")[:2000],
            model="none",
            mask="chronicler",
            status="live",
        )
    return {
        "ok": True,
        "ingested": True,
        "url": final,
        "ctype": ctype,
        "matrix": matrix,
        "path": str(dest),
        "whi": (stored or {}).get("whi") or "0x-WEB",
        "title": title,
        "stored": stored,
    }
