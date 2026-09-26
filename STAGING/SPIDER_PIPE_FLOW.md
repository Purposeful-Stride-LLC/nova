NOVA web spider + ingest pipe (palace refinement)
================================================
Steward: Grok Bot | Operator: Michael | 2026-09-21
A-F locked as HANDLING STAGES (not only MoE seat names).

A Scout     — is this URL/host worth the palace? primary/gov/academic preferred
B Analyst   — extract claims, numbers, systems; note uncertainty
C Skeptic   — challenge weak evidence / hype / missing controls
D Synthesist— merge multi-source into one coherent brief
E Chronicler— WHI stamp + provenance header (source, accessed, llm, mask)
F Sentinel  — risk / ROE gate before any outbound act

WHAT THE OLD POLITE SPIDER DID (heritage intent)
------------------------------------------------
1) Seed URL or topic → polite same-host crawl (delay 5–15s)
2) Fetch HTML → strip scripts/styles → plain text chunks
3) Pre-LLM matrix weigh (length, unique words, sentence mean, CAPS, density)
4) Reject thin/JS shells (Tx-REJECT) OR accept
5) Chunk text for LLM context size
6) LLM summary under a system prompt / mask
7) Store in palace with wing code

WHAT LIVE CODE HAD (gap)
------------------------
crawl.py  : fetch → Tx-TEMP chunks + auto fact. Matrix score now recorded on temps.
            Did NOT auto-run matrix reject or LLM summary.
hands/web.py : fetch → matrix → 0x-WEB raw OR Tx-REJECT. No LLM summary, no mask/llm stamp.
rag.py    : searches chunks.status=live only.
chamber   : temps/facts; promote_to_rag(case) exists for council → live.

NEW PIPE (nova/ingest_pipe.py)
------------------------------
process_url(url):
  hands.web.fetch → matrix
  if reject/score-low → Tx-REJECT fact, stop
  else summarize(model, mask) → store_accepted:
    live chunk + fact with header:
      source_url=  accessed=  llm=  mask=  matrix_score=  content_hash=  whi=

crawl.drain_temps_through_pipe(chunk_ids|limit):
  for each crawl temp → process_crawl_chunk (same weigh→summary→live/clear)

TRIGGERS (no breaks)
--------------------
Personal: /web URL  |  /crawl URL  |  ingest_pipe.process_url  |  GUI URL drop
Daemon:   board.enqueue_url → job ingest (sched) → should call pipe (wire next)
Cron-ish: /job add SECS crawl:URL  |  future job ingest-drain

WHI KEY GENERATOR
-----------------
nova/whi.py classify(kind/title/body/url) → Ax-|Tx-|0x-
Indexes: idx_facts_whi, idx_chunks_whi
Hunt: /hunt Ax-… or words
Council reports: currently Ax-CHAMBER facts + Tx-TEMP opinions;
  NOT in /rag until promote_to_rag (manual/pilot). Decision: auto after verdict?

DB SATURATION (~1000+ crawls)
----------------------------
Single SQLite NOVA.db today. Options for later council:
  1) Keep one DB + prune cleared temps aggressively
  2) Split by WHI wing into attached DBs (facts_0x.db, facts_Ax.db)
  3) Move chunks to separate chunks.db; facts stay core
  4) Different engine (only if SQLite proven insufficient)

FLOW (happy path)
-----------------
seed → crawl/fetch → matrix(A weigh) → [small-model INCLUDE?] →
summary under B/D mask → E chronicler stamp → live chunk+fact →
/rag retrieve + small gate → Ollama answer
F sentinel only if act/outbound.

