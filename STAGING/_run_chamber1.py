from nova import chamber
import json
problem = """Design NOVA memory-palace RAG for TUF.
Constraints: overlay nova/ only; never wipe data/NOVA.db; HIL before destructive.
Heritage: D:/pg/crawl/g3crawler.py (requests+BS4, sqlite url/code/title/content, 5-15s delay, hex classify). Fieldkit already has hands/web.py -> 0x-WEB + web_last.txt and board queue drain.
Need: chunks table (temp|live|cleared), crawl depth limit, summarize then promote, clear Tx-TEMP after judgment.
Deliberation: chamber/<case>/<seat> addresses. Who implements what: claw vs qwen code.
"""
print("starting round_robin...", flush=True)
out = chamber.round_robin("rag-crawl-framework", problem)
print(json.dumps(out, indent=2)[:4000])
print("--- temps ---")
print(json.dumps(chamber.list_temps(out["case"]), indent=2)[:2000])
