"""NOVA crawl — g3crawler heritage. Depth-limited. Writes temp chunks; no DB wipe."""
from __future__ import annotations
import hashlib
import random
import time
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from nova import db, whi, matrix

UA = "NOVA-fieldkit-crawl/1.0 (+local; steward HIL)"
MIN_DELAY, MAX_DELAY = 5.0, 15.0

class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.links, self.title, self._cap = [], [], "", False
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.links.append(d["href"])
        if tag == "title":
            self._cap = True
    def handle_endtag(self, tag):
        if tag == "title":
            self._cap = False
    def handle_data(self, data):
        if self._cap:
            self.title += data
        elif data and data.strip():
            self.parts.append(data.strip())

def _ensure(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS chunks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      zulu TEXT NOT NULL,
      whi TEXT NOT NULL,
      source_cite TEXT NOT NULL,
      text TEXT NOT NULL,
      hash TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'temp'
    );""")

def classify(text: str, url: str) -> str:
    """Claw hexclass (1x03/1x04/G1000/1x00) — kept for cite tags."""
    return whi.claw_hexclass(text, url)


def fetch(url: str, timeout: float = 15.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(200_000)
    html = raw.decode("utf-8", errors="ignore")
    p = _Text(); p.feed(html)
    text = " ".join(p.parts)[:12000]
    return {"ok": True, "title": (p.title or "")[:200], "text": text, "links": p.links[:40]}

def ingest_temp(url: str, text: str, title: str, depth: int) -> int:
    con = db.connect(); _ensure(con)
    title = (title or "").strip() or url
    m = matrix.analyze(text or "")
    body = (
        f"title={title}\ndepth={depth}\nurl={url}\nmatrix_score={m.get('score')}\n"
        f"matrix_label={m.get('label')}\n\n{text}"
    )[:8000]
    hx = hashlib.sha256(body.encode()).hexdigest()[:16]
    code = classify(text, url)
    # Thin pages still land as temp for steward audit; pipe later clears/rejects
    con.execute(
        "INSERT INTO chunks(zulu,whi,source_cite,text,hash,status) VALUES (?,?,?,?,?,?)",
        (db.zulu(), "Tx-TEMP", f"crawl:{code}:{url}", body, hx, "temp"),
    )
    con.commit(); cid = int(con.execute("SELECT last_insert_rowid()").fetchone()[0]); con.close()
    db.put_fact("auto", title[:160], body[:4000], kind="crawl", source_url=url, fallback_title=f"crawl/{hx}")
    return cid

def promote(chunk_id: int, summary: str) -> dict:
    con = db.connect(); _ensure(con)
    row = con.execute("SELECT * FROM chunks WHERE id=?", (chunk_id,)).fetchone()
    if not row: con.close(); return {"ok": False, "error": "missing"}
    summary = (summary or row["text"])[:2000]
    con.execute("UPDATE chunks SET status='live', whi=?, text=? WHERE id=?", ("0x-WEB", summary, chunk_id))
    con.commit(); con.close()
    title = f"chunk/{chunk_id}"
    raw = row["text"] or ""
    if raw.startswith("title="):
        title = raw.split("\n", 1)[0][6:].strip()[:160] or title
    db.put_fact("0x-WEB", title, summary[:4000], kind="web")
    return {"ok": True, "id": chunk_id}

def clear_temp_chunks(older_than_zulu: str | None = None, all_temp: bool = False) -> int:
    """Clear crawl temp chunks. all_temp=True clears every status=temp (steward prune)."""
    con = db.connect(); _ensure(con)
    if all_temp:
        n = con.execute("UPDATE chunks SET status='cleared' WHERE status='temp'").rowcount
    elif older_than_zulu:
        n = con.execute("UPDATE chunks SET status='cleared' WHERE status='temp' AND zulu<?", (older_than_zulu,)).rowcount
    else:
        n = 0
    con.commit(); con.close(); return int(n or 0)

def crawl(start_url: str, max_pages: int = 5, max_depth: int = 3, min_delay: float | None = None, max_delay: float | None = None, same_host: bool = True, enqueue_web: bool = False) -> dict:
    start_url = (start_url or "").strip()
    if not start_url.startswith("http"):
        return {"ok": False, "error": "need http(s)"}
    host0 = urlparse(start_url).netloc.lower()
    visited, q, pages, ids, enq = set(), [(start_url, 0)], 0, [], []
    while q and pages < max_pages:
        url, depth = q.pop(0)
        if url in visited or depth > max_depth: continue
        visited.add(url)
        try:
            page = fetch(url)
            cid = ingest_temp(url, page["text"], page["title"], depth)
            ids.append(cid); pages += 1
            if enqueue_web:
                try:
                    from nova import board
                    jid = board.enqueue_url(url)
                    if jid > 0:
                        enq.append(jid)
                    else:
                        # Failed to enqueue, skip recording
                        pass
                except Exception as exc:
                    db.put_fact("Tx-CRAWL-ENQUEUE", "err", f"{url}:{exc}"[:1000])
                    # Continue without adding to enq
            if depth < max_depth:
                for href in page.get("links") or []:
                    abs_u = urljoin(url, href)
                    pu = urlparse(abs_u)
                    if pu.scheme not in ("http", "https") or abs_u in visited:
                        continue
                    if same_host and pu.netloc.lower() != host0:
                        continue
                    # skip pure fragment duplicates of same path
                    q.append((abs_u.split("#", 1)[0], depth + 1))
            time.sleep(random.uniform(min_delay if min_delay is not None else MIN_DELAY, max_delay if max_delay is not None else MAX_DELAY))
        except Exception as exc:
            db.put_fact("Tx-CRAWL", "err", f"{url}:{exc}"[:2000])
    return {"ok": True, "pages": pages, "chunk_ids": ids, "visited": len(visited), "enqueued": enq, "host": host0}


def drain_temps_through_pipe(
    chunk_ids: list[int] | None = None,
    *,
    model: str = "qwen3:8b",
    mask: str = "chronicler",
    min_score: int = 28,
    limit: int = 20,
) -> dict:
    """Run matrix+LLM provenance promote on crawl temp chunks via ingest_pipe."""
    from nova import ingest_pipe
    con = db.connect(); _ensure(con)
    if chunk_ids:
        rows = []
        for cid in chunk_ids:
            r = con.execute("SELECT id FROM chunks WHERE id=? AND status='temp'", (cid,)).fetchone()
            if r:
                rows.append(r)
    else:
        rows = con.execute(
            "SELECT id FROM chunks WHERE status='temp' AND source_cite LIKE 'crawl:%' ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    con.close()
    out = []
    for r in rows:
        out.append(ingest_pipe.process_crawl_chunk(int(r["id"]), model=model, mask=mask, min_score=min_score))
    return {"ok": True, "n": len(out), "results": out}
