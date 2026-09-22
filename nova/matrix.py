"""Pre-LLM matrix. No model. Quality is 'is this page worth a wing' not morality."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter

STOP = set(
    """the a an and or of to in for on with at by from as is are was were be been
    this that it its you your we they them not but if then than so at""".split()
)


def strip_html(raw: str) -> str:
    title = ""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    if m:
        title = re.sub(r"\s+", " ", m.group(1))
    metas = re.findall(
        r'(?is)<meta[^>]+(?:name|property)=["\'](?:description|og:description|og:title)["\'][^>]+content=["\']([^"\']+)',
        raw,
    )
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&\w+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    head = " ".join([title] + metas)
    return (head + " " + text).strip()


def analyze(text: str, html_len: int = 0) -> dict:
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", text)
    low = [w.lower() for w in words]
    sents = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    lengths = [len(s.split()) for s in sents] or [0]
    mean = sum(lengths) / max(len(lengths), 1)
    caps = sum(1 for w in words if w.isupper() and len(w) > 2)
    unique = {w for w in low if w not in STOP and len(w) > 3}
    ranked = Counter(w for w in low if w not in STOP and len(w) > 3).most_common(12)
    density = (len(text) / html_len) if html_len else 1.0
    # quality 0-100: substance, not thin SEO
    score = 0
    score += 25 if len(text) > 800 else int(len(text) / 32)
    score += 15 if len(unique) > 40 else int(len(unique) / 3)
    score += 10 if 8 <= mean <= 28 else 0
    score += 10 if density > 0.08 else 0
    score -= min(20, caps)
    score = max(0, min(100, score))
    label = "ingest" if (score >= 28 and len(text) > 180) or len(unique) >= 30 else "reject-thin"
    return {
        "chars": len(text),
        "words": len(words),
        "unique": len(unique),
        "sents": len(sents),
        "mean_sent": round(mean, 1),
        "caps": caps,
        "text_ratio": round(density, 3),
        "top": ranked,
        "score": score,
        "label": label,
        "hash": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16],
    }


def dump(m: dict) -> str:
    return json.dumps({k: v for k, v in m.items() if k != "top"} | {"top": m.get("top")}, ensure_ascii=False)

def page_title(raw: str) -> str:
    """HTML <title> only, cleaned; empty if missing."""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw or "")
    if not m:
        return ""
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    t = re.split(r"\s*[|\u2013\u2014]\s*Contents", t)[0].strip()
    return t[:160]
