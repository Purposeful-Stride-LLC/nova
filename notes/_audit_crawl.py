import json
from pathlib import Path
from nova import board, db

# Finish draining any remaining http queue
left = []
for _ in range(20):
    r = board.drain_one()
    if r.get("empty"):
        break
    left.append(r)
    print("extra_drain", r.get("id"), (r.get("fetch") or {}).get("ingested"), r.get("url"))

z0 = "2026-09-19T13:49:05Z"
targets = [
    "doc.qt.io",
    "textual.textualize.io",
    "rich.readthedocs.io",
    "python-prompt-toolkit.readthedocs.io",
    "docs.python.org/3/library/curses",
    "urwid.org",
    "blessed.readthedocs.io",
]

con = db.connect()
facts = [dict(r) for r in con.execute(
    "SELECT id,zulu,whi,title,substr(body,1,100) head FROM facts WHERE zulu>=? ORDER BY id",
    (z0,),
).fetchall()]
chunks = [dict(r) for r in con.execute(
    "SELECT id,zulu,whi,source_cite,status,length(text) AS n FROM chunks WHERE zulu>=? ORDER BY id",
    (z0,),
).fetchall()]
queue = [dict(r) for r in con.execute(
    "SELECT id,zulu,status,description FROM queue WHERE id>=6 ORDER BY id"
).fetchall()]

# Classify our 10
seed = [
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

def match_fact(url):
    hits = []
    for f in facts:
        if url.rstrip("/") in (f.get("title") or "") or url.rstrip("/") in (f.get("head") or ""):
            hits.append(f)
        # body may contain url in 0x-WEB from crawl cite
    # also search full body for url
    rows = con.execute(
        "SELECT id,whi,title FROM facts WHERE zulu>=? AND body LIKE ?",
        (z0, f"%{url[:40]}%"),
    ).fetchall()
    for r in rows:
        hits.append(dict(r))
    return hits

audit = {"seeds": [], "note": "web path uses quality gate; crawl path writes Tx-TEMP chunks"}
for u in seed:
    qrow = next((q for q in queue if q["description"] == u), None)
    ch = [c for c in chunks if u in (c.get("source_cite") or "")]
    # facts 0x-WEB/Tx-REJECT around same time - match by scanning matrix path
    fhits = [dict(r) for r in con.execute(
        "SELECT id,whi,title FROM facts WHERE zulu>=? AND (body LIKE ? OR title LIKE ?)",
        (z0, f"%{u.split('//',1)[-1][:50]}%", f"%{u.split('//',1)[-1][:40]}%"),
    ).fetchall()]
    audit["seeds"].append({
        "url": u,
        "queue": qrow,
        "web_facts": fhits,
        "crawl_chunks": ch,
        "web_ok": any(f.get("whi") == "0x-WEB" for f in fhits),
        "web_reject": any(f.get("whi") == "Tx-REJECT" for f in fhits),
        "crawl_ok": len(ch) > 0,
    })

summary = {
    "seeds_total": 10,
    "queue_done": sum(1 for s in audit["seeds"] if (s.get("queue") or {}).get("status") == "done"),
    "queue_fail": sum(1 for s in audit["seeds"] if (s.get("queue") or {}).get("status") == "fail"),
    "web_0x": sum(1 for s in audit["seeds"] if s["web_ok"]),
    "web_reject": sum(1 for s in audit["seeds"] if s["web_reject"]),
    "crawl_chunked": sum(1 for s in audit["seeds"] if s["crawl_ok"]),
    "chunks_total_since": len(chunks),
    "extra_drains": [
        {"id": r.get("id"), "ingested": (r.get("fetch") or {}).get("ingested"), "url": r.get("url")}
        for r in left
    ],
}
con.close()
out = {"summary": summary, "audit": audit}
Path("STAGING/CRAWL_AUDIT_GUI_TUI.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
for s in audit["seeds"]:
    print(
        "SEED",
        "web=" + ("OK" if s["web_ok"] else ("REJ" if s["web_reject"] else "MISS")),
        "crawl=" + ("OK" if s["crawl_ok"] else "MISS"),
        "q=" + str((s.get("queue") or {}).get("status")),
        s["url"][:70],
    )
