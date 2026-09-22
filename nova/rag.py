"""RAG over palace chunks/facts. Small-model gate before big prompt."""

from __future__ import annotations

import json
import re
from collections import Counter

from nova import db


def _tokens(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9_]{3,}", (s or "").lower()) if w]


def search(query: str, limit: int = 12, status: str = "live") -> list[dict]:
    """Word-count weight search over live chunks (+ optional 0x-WEB facts)."""
    q = _tokens(query)
    if not q:
        return []
    qset = set(q)
    con = db.connect()
    rows = con.execute(
        "SELECT id,zulu,whi,source_cite,text,hash,status FROM chunks WHERE status=? ORDER BY id DESC LIMIT 400",
        (status,),
    ).fetchall()
    scored = []
    for r in rows:
        text = r["text"] or ""
        toks = _tokens(text)
        if not toks:
            continue
        c = Counter(toks)
        # term frequency overlap weight
        score = sum(c[t] for t in qset)
        # subject bonus if cite/host matches query tokens
        cite = (r["source_cite"] or "").lower()
        score += 3 * sum(1 for t in qset if t in cite)
        if score <= 0:
            continue
        scored.append(
            {
                "id": r["id"],
                "score": score,
                "whi": r["whi"],
                "cite": r["source_cite"],
                "hash": r["hash"],
                "snippet": text[:500],
            }
        )
    scored.sort(key=lambda x: (-x["score"], -x["id"]))
    con.close()
    return scored[:limit]


def _small_judge(query: str, snippet: str, model: str = "qwen2:0.5b") -> dict:
    """Tiny local model gate; first line of chunk must be INCLUDE|EXCLUDE only."""
    import urllib.request
    
    # Strip the first-line directive from snippet if present and parse it strictly
    lines = [l for l in (snippet or "").splitlines()][:1]
    first_line = lines[0].strip() if lines else ""
    directive_only = first_line.upper() in {"INCLUDE", "EXCLUDE"} and len(first_line) <= 9
    
    prompt = (
        f"Query: {query[:200]}\nChunk (skip first line for context): {snippet[:400]}\n"
        "Reply ONLY: INCLUDE or EXCLUDE then one short reason."
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You gate RAG chunks. Be strict. Junk or off-topic = EXCLUDE."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "keep_alive": 0,
    }
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode())
        text = ((data.get("message") or {}).get("content") or "").strip()
        head = text.splitlines()[0].upper() if text else ""
        # If the chunk's first line was already directive-only, trust that directive
        if directive_only:
            include = first_line.upper() == "INCLUDE"
            raw = f"DIRECTIVE:{first_line}"
        elif head.startswith("EXCLUDE"):
            include = False
            raw = text[:300]
        else:
            include = head.startswith("INCLUDE")
            raw = text[:300]
        return {"include": include, "raw": raw, "model": model}
    except Exception as exc:
        # fail-open on score alone if tiny model down
        return {"include": True, "raw": f"gate-error:{exc}", "model": model}


def retrieve(query: str, limit: int = 5, gate: bool = True, model: str = "qwen2:0.5b") -> dict:
    """Search then rapid include/exclude evaluations. Returns worthy snippets only."""
    hits = search(query, limit=max(limit * 3, 12))
    kept, dropped = [], []
    for h in hits:
        if not gate:
            kept.append(h)
        else:
            j = _small_judge(query, h["snippet"], model=model)
            row = {**h, "gate": j}
            (kept if j.get("include") else dropped).append(row)
        if len(kept) >= limit:
            break
    # stamp a brief ledger fact for orientation (not junk body)
    db.put_fact(
        "Ax-RAG",
        f"retrieve:{query[:40]}",
        json.dumps({"kept": len(kept), "dropped": len(dropped), "q": query[:120]})[:2000],
    )
    return {
        "ok": True,
        "zulu": db.zulu(),
        "query": query,
        "kept": kept[:limit],
        "dropped": dropped[:20],
    }


def context_block(query: str, limit: int = 4) -> str:
    """Text block for LLM prompts; call after retrieve."""
    r = retrieve(query, limit=limit, gate=True)
    parts = []
    for i, h in enumerate(r.get("kept") or [], 1):
        parts.append(f"[{i}] cite={h.get('cite')} score={h.get('score')}\n{h.get('snippet')}")
    return "\n\n".join(parts)
