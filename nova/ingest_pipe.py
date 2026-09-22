"""Simulation-only ingest pipe for the NOVA fieldkit mirror.

This module is deliberately side-effect free: it does not fetch URLs, open NOVA.db,
write chunks/facts, or call an LLM. It adapts the existing ``nova.matrix`` and
``nova.whi`` interfaces into a dry-run pipeline for local tests and documentation.
"""
from __future__ import annotations

from typing import Any

from nova.matrix import analyze, dump, page_title, strip_html
from nova.whi import classify, classify_web


def _summary(text: str, title: str = "", mask: str = "brief", limit: int = 800) -> str:
    """Make a deterministic dry summary; ``mask`` records the requested seat."""
    clean = " ".join((text or "").split())
    sentences = [part.strip() for part in clean.replace("!", ".").replace("?", ".").split(".") if part.strip()]
    body = ". ".join(sentences[:3])
    if body and not body.endswith("."):
        body += "."
    prefix = f"[{mask} simulation] "
    if title:
        prefix += f"{title}: "
    return (prefix + body)[:limit]


def simulate(raw: str, *, url: str = "", title: str = "", mask: str = "brief") -> dict[str, Any]:
    """Run fetch/strip, matrix gate, summary, and WHI classification in memory.

    ``raw`` may be HTML or already-extracted text. The return value is a packet
    suitable for inspection or a later adapter; no persistent state is changed.
    """
    source = raw or ""
    looks_html = "<" in source and ">" in source
    text = strip_html(source) if looks_html else source
    page = page_title(source) if looks_html else ""
    title = (title or page or url).strip()
    metrics = analyze(text, html_len=len(source) if looks_html else 0)
    packet: dict[str, Any] = {
        "ok": True,
        "dry_run": True,
        "url": url,
        "title": title,
        "matrix": metrics,
        "matrix_json": dump(metrics),
        "stage": "skeptic",
        "writes": [],
    }
    if metrics["label"] != "ingest":
        packet.update({"decision": "reject", "whi": "Tx-REJECT", "reason": metrics["label"]})
        return packet

    packet["decision"] = "ingest"
    packet["stage"] = "synthesist"
    packet["summary"] = _summary(text, title, mask)
    packet["stage"] = "chronicler"
    packet["whi"] = classify_web(text, url, title)["whi"] if url else classify(
        text, title=title, kind="web", default="0x-WEB"
    )
    packet["cite"] = f"web:{url or title}"
    packet["stage"] = "sentinel"
    packet["next"] = "live chunk/fact -> /rag (not performed in simulation)"
    return packet


__all__ = ["simulate"]
