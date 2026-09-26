import json
from pathlib import Path
from nova import crawl, db, board

z0 = db.zulu()
print("DEEP START", z0, flush=True)
jobs = [
    ("https://textual.textualize.io/guide/", 10, 2),
    ("https://textual.textualize.io/guide/CSS/", 6, 2),
    ("https://doc.qt.io/qtforpython/", 10, 2),
    ("https://doc.qt.io/qtforpython-6/quickstart.html", 6, 2),
]
results = []
for url, mp, md in jobs:
    print("CRAWL", url, "pages", mp, "depth", md, flush=True)
    r = crawl.crawl(url, max_pages=mp, max_depth=md, min_delay=2.5, max_delay=5.0, same_host=True, enqueue_web=True)
    results.append({"seed": url, **r})
    print("  ->", {k: r.get(k) for k in ("ok","pages","chunk_ids","enqueued","host","error")}, flush=True)

# Drain some of the newly enqueued for web gate (limit 25 to avoid forever)
drained = []
for _ in range(25):
    d = board.drain_one()
    if d.get("empty"):
        break
    f = d.get("fetch") or {}
    drained.append({"id": d.get("id"), "url": d.get("url"), "ingested": f.get("ingested"), "label": (f.get("matrix") or {}).get("label")})
    print("drain", drained[-1], flush=True)

con = db.connect()
chunks = [dict(x) for x in con.execute(
    "SELECT id,status,substr(source_cite,1,120) c,length(text) n FROM chunks WHERE zulu>=? ORDER BY id",
    (z0,),
).fetchall()]
# promote on-topic temp chunks (textual or qtforpython in cite) to live
promoted = []
for ch in con.execute("SELECT id,source_cite,text FROM chunks WHERE status='temp'").fetchall():
    cite = ch["source_cite"] or ""
    if "textual.textualize.io" in cite or "doc.qt.io/qtforpython" in cite:
        from nova import crawl as C
        # short summary = first 600 chars
        summary = (ch["text"] or "")[:600]
        C.promote(ch["id"], summary)
        promoted.append(ch["id"])
# clear off-topic temps (e.g. python.org)
cleared = con.execute(
    "UPDATE chunks SET status='cleared' WHERE status='temp' AND source_cite LIKE '%python.org%'"
).rowcount
con.commit()
con.close()
out = {"z0": z0, "z1": db.zulu(), "results": results, "drained": drained, "new_chunks": len(chunks), "promoted": promoted, "cleared_python_org": cleared}
Path("STAGING/DEEP_CRAWL_QT_TEXTUAL.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({k: out[k] for k in out if k != "results"}, indent=2), flush=True)
print("pages", sum(r.get("pages") or 0 for r in results), "promoted", len(promoted), flush=True)
