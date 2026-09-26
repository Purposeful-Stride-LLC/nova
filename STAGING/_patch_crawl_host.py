from pathlib import Path
p = Path("nova/crawl.py")
t = p.read_text(encoding="utf-8")
if "same_host: bool" in t:
    print("same_host already")
else:
    t = t.replace(
        "def crawl(start_url: str, max_pages: int = 5, max_depth: int = 3, min_delay: float | None = None, max_delay: float | None = None) -> dict:",
        "def crawl(start_url: str, max_pages: int = 5, max_depth: int = 3, min_delay: float | None = None, max_delay: float | None = None, same_host: bool = True, enqueue_web: bool = False) -> dict:",
    )
    # after start_url strip and http check, capture host
    old = '''    visited, q, pages, ids = set(), [(start_url, 0)], 0, []
    while q and pages < max_pages:
        url, depth = q.pop(0)
        if url in visited or depth > max_depth: continue
        visited.add(url)
        try:
            page = fetch(url)
            cid = ingest_temp(url, page["text"], page["title"], depth)
            ids.append(cid); pages += 1
            if depth < max_depth:
                for href in page.get("links") or []:
                    abs_u = urljoin(url, href)
                    if urlparse(abs_u).scheme in ("http", "https") and abs_u not in visited:
                        q.append((abs_u, depth + 1))
'''
    new = '''    host0 = urlparse(start_url).netloc.lower()
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
                    enq.append(board.enqueue_url(url))
                except Exception:
                    pass
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
'''
    if old not in t:
        raise SystemExit("crawl loop block missing")
    t = t.replace(old, new, 1)
    t = t.replace(
        'return {"ok": True, "pages": pages, "chunk_ids": ids, "visited": len(visited)}',
        'return {"ok": True, "pages": pages, "chunk_ids": ids, "visited": len(visited), "enqueued": enq, "host": host0}',
    )
    p.write_text(t, encoding="utf-8")
    print("patched crawl same_host+enqueue")
