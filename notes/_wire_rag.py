from pathlib import Path
p = Path("nova/tui/term.py")
t = p.read_text(encoding="utf-8")
if 'startswith("/rag")' in t:
    print("/rag already")
else:
    needle = '    if low.startswith("/crawl"):'
    block = '''    if low.startswith("/rag"):
        from nova import rag

        rest = raw[4:].strip()
        if not rest:
            return "usage: /rag QUERY"
        return str(rag.retrieve(rest, limit=4))[:1200]

'''
    if needle not in t:
        needle = '    if low.startswith("/web"):'
    t = t.replace(needle, block + needle, 1)
    p.write_text(t, encoding="utf-8")
    print("wired /rag")
t = p.read_text(encoding="utf-8")
if "/rag Q" not in t:
    t = t.replace(
        "/web URL  /crawl URL  /hunt Q  /pdf PATH  /codesum PATH",
        "/web URL  /crawl URL  /rag Q  /hunt Q  /pdf PATH  /codesum PATH",
        1,
    )
    p.write_text(t, encoding="utf-8")
    print("HELP /rag")
