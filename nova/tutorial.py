PAGES = [
    """PAGE 1  QUICK START
Two windows in NOVA  (or ~/NOVA):
  python -m nova          daemon
  python -m nova.tui      this face
/help  /tutorial 2  /tools  /jobs  /suggest
""",
    """PAGE 2  JOBS
Daemon ticks the jobs table. TUI only edits it.
  /jobs
  /job add 300 holmes
  /job add 600 ollama-catalog
  /job on ID     /job off ID
  /tick          run due jobs now
Unknown names error in master.log. Known: holmes maintain ollama-catalog
""",
    """PAGE 3  WEB INJECT
  /web https://www.spacex.com
Fetch → strip scripts → matrix (length, unique words, sentence mean, CAPS)
Score >= 45 and >400 chars → 0x-WEB with URL+hash
Else Tx-REJECT (thin/JS page). Open data\\artifacts\\web_last.txt
JS-only homepages often reject. Try a text-heavy URL (news, docs, blog).
""",
    """PAGE 4  MODELS
  /models           stamps each tag as Ax-OLLAMA
  /model NAME       pin that tag for /ask
Router: short yes/no → 0.5B/sentinel if present, else 8B.
Ollama loads whatever name you pin. Loopback only.
""",
    """PAGE 5  PALACE
  /hunt words       no LLM
  /conv new         numbered talk
  /codesum PATH     file or folder → Tx-CODE then promote
  /pdf FILE.pdf     text layer only
NOVA home is the folder that contains nova\\ and data\\.
""",
    """PAGE 6  VOICE AND CAM
Keep  python -m pocket_tts serve --default-voice anna   on :8000
  /tts hello    /voice anna|michael|jane|eve
  /cam 0        local still
Writes data\\artifacts\\ with real extensions.
""",
    """PAGE 7  CLAW LEASH
OpenClaw is a servant on 127.0.0.1:18789 — not the palace.
  /claw              status (TCP)
  /claw do the thing ask via HTTP if chatCompletions enabled
  /job add 120 claw-ping
  /job add 300 claw-run
  /qwen PROMPT       qwen --prompt subprocess valet
  /job add 600 qwen:Say pong
Driver for tool STEPs: ollama/qwen3.5:9b (32k). lobster 8b overflows bootstrap.
Write path rule: Claw writes under ~/.openclaw/workspace/nova-out/ then NOVA pulls.
Never treat deliver_inbox as real Claw (that is Ollama mask mail).
""",
    """PAGE 8  MAIL + MEMORY SEEDS
leash.handoff -> packets -> openclaw_run/claw-run -> stamp delivered + brief@local reply.
Shared zulu clock. WHI: Ax- ok, Tx- break/task, 0x- web/artifact.
After leash gap-close: tighten RAG on facts/packets, then /web ingest into the memory palace.
""",
    """PAGE 9  CRAWL / WEB / RAG
/crawl URL     same-host explore -> chunks (daemon: crawl:URL)
/web URL       quality gate -> 0x-WEB or Tx-REJECT
/rag QUERY     word-weight search + small-model INCLUDE/EXCLUDE
Pipeline: crawl may enqueue URLs; daemon ingest drains to web.fetch.
Base glass: deepen Textual + Qt. Facts stay precise; gate filters prompt only.
""",
    """PAGE 10  CHAMBER + DIARY
/chamber list CASE   /chamber clear CASE
Seats: claw + code + brief. Temps = Tx-TEMP (not RAG). promote_to_rag(case) -> live.
Diary: GrokBot.log.ai append-only. Re-scan when stuck - ponderings are fuel.
""",
    """PAGE 11  MASKS / WHI / WA / PROOF
/mask list|auto|NAME   (masks.py cues; not Modelfile jackets)
/hunt Ax-CHAMBER       facts; /rag needs live chunks
/wa link               QR then HIL send; bridge via openclaw :18789
Claw: PROOF: bytes=N before DONE; write to nova-out; steward pulls.
START_NOVA.bat: titled TTS (:8000 anna) + daemon + GUI. Astrocomms = multiline Ctrl+Enter.
""",
]


def page(n: int) -> str:
    if n < 1:
        n = 1
    if n > len(PAGES):
        n = len(PAGES)
    return PAGES[n - 1] + f"\n({n}/{len(PAGES)})  /tutorial {n+1 if n < len(PAGES) else 1}"
