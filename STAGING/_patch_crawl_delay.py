from pathlib import Path
p = Path("nova/crawl.py")
t = p.read_text(encoding="utf-8")
if "min_delay: float" in t:
    print("delay kwargs already")
else:
    t = t.replace(
        "def crawl(start_url: str, max_pages: int = 5, max_depth: int = 3) -> dict:",
        "def crawl(start_url: str, max_pages: int = 5, max_depth: int = 3, min_delay: float | None = None, max_delay: float | None = None) -> dict:",
    )
    t = t.replace(
        "time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))",
        "time.sleep(random.uniform(min_delay if min_delay is not None else MIN_DELAY, max_delay if max_delay is not None else MAX_DELAY))",
    )
    p.write_text(t, encoding="utf-8")
    print("patched crawl delays")
