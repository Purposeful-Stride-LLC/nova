from pathlib import Path
p = Path("nova/sched.py")
t = p.read_text(encoding="utf-8")
if 'startswith("crawl:")' in t:
    print("crawl job already")
else:
    needle = '        elif key.startswith("qwen:"):'
    block = '''        elif key.startswith("crawl:"):
            from nova import crawl as crawlmod

            url = key.split(":", 1)[1].strip()
            note = str(crawlmod.crawl(url, max_pages=3, max_depth=2))[:200]
'''
    if needle not in t:
        raise SystemExit("no qwen needle")
    p.write_text(t.replace(needle, block + needle, 1), encoding="utf-8")
    print("wired crawl:")
