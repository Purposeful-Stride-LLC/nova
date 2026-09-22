from nova import chamber, db
import json

case = "20260919T1334-f4b6ead4"
# Defense re-ask qwen — BASIC, no agent chat fluff
qprompt = """DESIGN ONLY. No questions back. Max 10 lines.
NOVA RAG: one chunks table status temp|live|cleared.
Crawl like g3crawler: requests+BS4, delay 5-15s, depth max 3, hex classify.
Promote: summarize then live. Clear Tx-TEMP after steward verdict.
Who codes what: claw writes python modules; qwen reviews paths.
State: schema fields, crawl steps, clear rule, top risk.
"""
print("re-ask qwen...", flush=True)
qop = chamber.ask_qwen(qprompt)
print(qop[:800], flush=True)
print(chamber.store_temp(case, "qwen-defense", qop, cite="chamber.defense:qwen"))

# Brief claw defense on: one table vs three; embeddings now or later
cprompt = """DEFENSE. Max 8 lines. Opponent wants 3 chunk tables. Argue for ONE chunks table with status column. Embeddings now or later? Prefer later. No file writes."""
print("claw defense...", flush=True)
cop = chamber.ask_claw(cprompt)
print(cop[:600], flush=True)
print(chamber.store_temp(case, "claw-defense", cop, cite="chamber.defense:claw"))

judgment = """STEWARD VERDICT case 20260919T1334-f4b6ead4
Adopt Claw spine + Code depth limit; reject Code's 3 physical tables; reject embeddings in v1.
SCHEMA: one chunks(id,zulu,whi,source_cite,text,hash,status) status in temp|live|cleared. Optional later: url,depth columns via ALTER.
CRAWL: port g3crawler pattern into nova/crawl.py — requests+BS4, UA, delay 5-15, max_pages/depth, hex classify from hexclass/whcs; enqueue via board; fetch may reuse hands/web for single URL.
FLOW: fetch -> Tx-TEMP/chunk temp -> summarize (chronicler or codesum short) -> status=live whi 0x-WEB or Ax-RAG -> clear Tx-TEMP for case.
TEMP WHI: title chamber/<case>/<seat>; clear_temps(case) after verdict+orders started.
RISKS: claw silent DONE (verify disk); qwen interactive fluff (BASIC prompts); aggressive purge (HIL); do not wipe NOVA.db.
ORDERS:
1) claw: write nova-out/crawl.py (g3 pattern, depth<=3, no delete without flag)
2) steward: pull/review into nova/crawl.py; wire sched crawl:URL; extend chamber already live
3) qwen later: review crawl.py paths only (not this minute)
4) embeddings deferred
"""
orders = {
    "claw": "write nova-out/crawl.py from g3 pattern depth<=3",
    "steward": "pull review wire sched; chamber clear after implement start",
    "qwen": "defer path review",
    "code": "depth 3 adopted; no 3-table split",
}
v = chamber.verdict(case, judgment, orders)
print("VERDICT", v["case"], flush=True)
# Keep temps until crawl.py lands — then clear
print("temps still held for audit", len(chamber.list_temps(case)))
