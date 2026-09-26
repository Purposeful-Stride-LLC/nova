"""Queue 10 GUI/TUI docs into board + crawl seed pages into chunks; drain web queue."""
from __future__ import annotations
import json
from nova import board, crawl, db
from nova.hands import web

URLS = [
    "https://doc.qt.io/qtforpython/",
    "https://doc.qt.io/qtforpython-6/quickstart.html",
    "https://textual.textualize.io/guide/",
    "https://textual.textualize.io/guide/CSS/",
    "https://rich.readthedocs.io/en/stable/introduction.html",
    "https://rich.readthedocs.io/en/stable/console.html",
    "https://python-prompt-toolkit.readthedocs.io/en/stable/",
    "https://docs.python.org/3/library/curses.html",
    "https://urwid.org/manual/overview.html",
    "https://blessed.readthedocs.io/en/latest/",
]

z0 = db.zulu()
print("START", z0, flush=True)
queued = []
for u in URLS:
    jid = board.enqueue_url(u)
    queued.append({"id": jid, "url": u})
    print("queued", jid, u, flush=True)

# Drain web ingest path (daemon-equivalent)
web_results = []
for i in range(len(URLS) + 2):
    r = board.drain_one()
    if r.get("empty"):
        break
    web_results.append(r)
    print("web_drain", r.get("id"), r.get("fetch", {}).get("ingested"), r.get("url"), flush=True)

# Crawl seed pages into chunks (exploratory depth 1, 2 pages max per seed; polite 3-6s)
crawl_results = []
for u in URLS:
    print("crawl", u, flush=True)
    cr = crawl.crawl(u, max_pages=2, max_depth=1, min_delay=3.0, max_delay=6.0)
    crawl_results.append({"url": u, **cr})
    print("  pages", cr.get("pages"), "chunks", cr.get("chunk_ids"), flush=True)

# Snapshot palace
con = db.connect()
facts_web = con.execute(
    "SELECT id,zulu,whi,title FROM facts WHERE zulu>=? AND whi IN ('0x-WEB','Tx-REJECT') ORDER BY id",
    (z0,),
).fetchall()
chunks = con.execute(
    "SELECT id,zulu,whi,substr(source_cite,1,80) cite,status,length(text) n FROM chunks WHERE zulu>=? ORDER BY id",
    (z0,),
).fetchall()
queue_rows = con.execute(
    "SELECT id,status,substr(description,1,80) url FROM queue WHERE zulu>=? ORDER BY id",
    (z0,),
).fetchall()
con.close()

report = {
    "zulu_start": z0,
    "zulu_end": db.zulu(),
    "queued": queued,
    "web_drains": [
        {
            "id": r.get("id"),
            "url": r.get("url"),
            "ingested": (r.get("fetch") or {}).get("ingested"),
            "ok": (r.get("fetch") or {}).get("ok"),
            "label": ((r.get("fetch") or {}).get("matrix") or {}).get("label"),
            "error": (r.get("fetch") or {}).get("error"),
        }
        for r in web_results
    ],
    "crawl": [{"url": c["url"], "pages": c.get("pages"), "chunk_ids": c.get("chunk_ids"), "ok": c.get("ok"), "error": c.get("error")} for c in crawl_results],
    "facts_new": [dict(r) for r in facts_web],
    "chunks_new": [dict(r) for r in chunks],
    "queue": [dict(r) for r in queue_rows],
}
Path = __import__("pathlib").Path
Path("STAGING/CRAWL_TEST_GUI_TUI.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("REPORT", Path("STAGING/CRAWL_TEST_GUI_TUI.json"), flush=True)
print(json.dumps({
    "web_ingested": sum(1 for x in report["web_drains"] if x.get("ingested")),
    "web_rejected_or_fail": sum(1 for x in report["web_drains"] if not x.get("ingested")),
    "crawl_pages": sum(c.get("pages") or 0 for c in crawl_results),
    "chunks": len(report["chunks_new"]),
    "facts": len(report["facts_new"]),
}, indent=2), flush=True)
