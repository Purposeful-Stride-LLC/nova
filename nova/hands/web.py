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


def fetch(url: str, cap: int = 120_000) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "http(s) only"}
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
    db.put_fact(
        "0x-WEB",
        title[:160],
        f"url={final}\n\n{text[:7800]}",
        source_url=final,
        content_hash=matrix["hash"],
        matrix_json=dump(matrix),
    )
    return {
        "ok": True,
        "ingested": True,
        "url": final,
        "ctype": ctype,
        "matrix": matrix,
        "path": str(dest),
        "whi": "0x-WEB",
        "title": title,
    }
