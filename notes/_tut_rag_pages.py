from pathlib import Path
p = Path("nova/tutorial.py")
t = p.read_text(encoding="utf-8")
if "PAGE 9  CRAWL" in t:
    print("tutorial.py already has crawl page")
else:
    extra = '''    """PAGE 9  CRAWL / WEB / RAG
/crawl URL     same-host explore -> chunks (daemon: crawl:URL)
/web URL       quality gate -> 0x-WEB or Tx-REJECT
/rag QUERY     word-weight search + small-model INCLUDE/EXCLUDE
Pipeline: crawl may enqueue URLs; daemon ingest drains to web.fetch.
Base glass: deepen Textual + Qt. Facts stay precise; gate filters prompt only.
""",
    """PAGE 10  CHAMBER + DIARY
/chamber list CASE   /chamber clear CASE
Tx-TEMP chamber/<case>/<seat> -> Ax-CHAMBER verdict -> clear.
Diary: GrokBot.log.ai append-only. Re-scan when stuck — ponderings are fuel.
""",
'''
    # insert before closing ]
    lines = t.splitlines(keepends=True)
    idx = next(i for i,l in enumerate(lines) if l.strip()=="]")
    for k in range(idx-1, -1, -1):
        if lines[k].strip():
            if not lines[k].rstrip().endswith(","):
                lines[k] = lines[k].rstrip("\r\n") + ",\n"
            break
    new = "".join(lines[:idx]) + extra + "".join(lines[idx:])
    p.write_text(new, encoding="utf-8")
    print("tutorial.py pages 9-10 added")
