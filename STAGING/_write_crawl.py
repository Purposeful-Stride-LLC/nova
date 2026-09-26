from pathlib import Path
raw = Path("STAGING/_claw_order_crawl.txt").read_text(encoding="utf-8")
body = raw.split("CONTENT:", 1)[1].split("RULES:", 1)[0].strip() + "\n"
Path("nova/crawl.py").write_text(body, encoding="utf-8")
out = Path(r"%USERPROFILE%\.openclaw\workspace\nova-out")
out.mkdir(parents=True, exist_ok=True)
(out / "crawl.py").write_text(body, encoding="utf-8")
print("bytes", Path("nova/crawl.py").stat().st_size)
import ast
ast.parse(body)
from nova import crawl, chamber
print("crawl fn", crawl.crawl)
print("clear", chamber.clear_temps("20260919T1334-f4b6ead4"))
