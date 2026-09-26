from pathlib import Path
p = Path("nova/tui/term.py")
t = p.read_text(encoding="utf-8")
if 'startswith("/crawl")' in t:
    print("/crawl already")
else:
    needle = '    if low.startswith("/web"):'
    block = '''    if low.startswith("/crawl"):
        from nova import crawl as crawlmod

        rest = raw[6:].strip()
        if not rest.startswith("http"):
            return "usage: /crawl https://URL   (daemon: crawl:URL or /job add)"
        return str(crawlmod.crawl(rest, max_pages=3, max_depth=2))[:800]

'''
    if needle not in t:
        raise SystemExit("no /web needle")
    t = t.replace(needle, block + needle, 1)
    p.write_text(t, encoding="utf-8")
    print("wired /crawl")
# HELP line
t = p.read_text(encoding="utf-8")
if "/crawl URL" not in t:
    t = t.replace(
        "/web URL  /hunt Q  /pdf PATH  /codesum PATH",
        "/web URL  /crawl URL  /hunt Q  /pdf PATH  /codesum PATH",
        1,
    )
    p.write_text(t, encoding="utf-8")
    print("HELP updated")
else:
    print("HELP ok")
