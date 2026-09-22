================================================================================
NOVA FIELD KIT
Purposeful Strides LLC  /  metal face  /  Python 3.10+
README  —  developer journal  —  2026-09-18
================================================================================

WHAT THIS IS
  Local homestead agent. Daemon ticks jobs. TUI is the window.
  Palace is SQLite under data\  (NEVER ship or overwrite that folder).
  Code overlay: copy nova\ only onto a live tree.

LAYOUT
  NOVA/                          steward home (or ...\NOVA_fieldkit_v1_4\)
    nova\                        this package
    data\                        LIVE. do not unzip over this
      NOVA.db
      artifacts\                 wav jpg md txt
      master.log  chat.log
    README.txt                   this file
    TUTORIAL.txt                 worked examples (AI-parseable)
    requirements.txt

START
  cd to the folder that contains nova\
  Window A:  python -m nova
  Window B:  python -m nova.tui
  Optional:  python -m pocket_tts serve --default-voice alba

  Daemon prints Zulu + db path + job list.
  TUI: /help   /tutorial   /forge

COPY RULE (iterations)
  Overlay nova\*.py + README.txt + TUTORIAL.txt
  Leave data\NOVA.db alone so PDF / web / history rows survive.

--------------------------------------------------------------------------------
DEPENDENTS  (cite these; they are not bundled)
--------------------------------------------------------------------------------
  Python 3.10+          C:\Python314 on the TUF
  Ollama                127.0.0.1:11434
                        tags used: llama3-groq-tool-use:8b qwen3:8b
                                   llama3.2:3b gemma2:2b llama3:8b
                                   qwen2:0.5b nova-* masks
  pocket-tts            Kyutai. serve = POST /tts form on :8000
                        generate = slow fallback (HF download)
  psutil                holmes cpu/ram
  opencv-python-headless  /cam  hw-check cameras
  pypdf                 /pdf text layer only
  certifi               optional SSL for /web

  Not required to boot: pymupdf, chroma, sqlite-vec, pygame, textual.

--------------------------------------------------------------------------------
DAEMON
--------------------------------------------------------------------------------
  Entry:  python -m nova
  Loop:   sched.tick() every 5s
  Jobs table in NOVA.db  (TUI edits, daemon runs)
  Known job names:
    holmes              hw-check           ollama-catalog
    maintain            whistle
    cam:N               web:URL
    codesum:PATH        pdf:PATH           history
  Log:    data\master.log  + table master_log
  Stop:   Ctrl+C

--------------------------------------------------------------------------------
TUI SLASH SURFACE  (see TUTORIAL.txt for worked cases)
--------------------------------------------------------------------------------
  /help /tutorial [n] /tools /forge /suggest /list
  /jobs /job add SECS NAME /job on ID /job off ID /tick
  /web URL /hunt Q /pdf PATH /codesum PATH /history
  /models /model NAME /mask NAME|list
  /conv new /holmes /queue /approve N /deny N
  /reports /ack ID /staff
  /tts TEXT /voice ID /cam [n] /see [n|PATH] /hear WAV /vision
  /quit

  Parser grammar the model may emit:
    [speak alba] one sentence [/speak]

--------------------------------------------------------------------------------
PALACE WINGS
--------------------------------------------------------------------------------
  Ax-*     self (models, hw after integrate)
  0x-WEB   ingested pages
  Tx-*     staging (PDF CODE CAM HIST REJECT HW)
  Gx       dormant

--------------------------------------------------------------------------------
JOURNAL  (append a dated line when a feature lands)
--------------------------------------------------------------------------------
  2026-09-17  v1.4 daemon + matrix + jobs
  2026-09-17  v1.5 restore commands, opencv, router
  2026-09-17  v1.6 office packets staff reports cam:N whistle 900s
  2026-09-17  fetch UA+SSL  looser ingest  staff bind to ollama tags
  2026-09-17  parser speak tags  /history Chrome copy
  2026-09-18  /forge  README.txt TUTORIAL.txt  code-only zip
  2026-09-18  senses /see /hear /vision  Tx-CAM Tx-EAR  GIS waits
  2026-09-18  DEVLOG.txt ascii/INDEX.txt STAGING patch bay

Cross-ref: every command in TUTORIAL.txt section COMMANDS.
================================================================================

--------------------------------------------------------------------------------
2026-09-19  v1.8+  leash · chamber · crawl · RAG gate  (Grok Bot diary sync)
--------------------------------------------------------------------------------
  Claw leash: openclaw_run / claw-run; tool STEPs prefer qwen3.5:9b; nova-out pull.
  Chamber: nova/chamber.py  Tx-TEMP chamber/<case>/<seat> then Ax-CHAMBER verdict.
  Crawl:   nova/crawl.py    same-host explore -> temp chunks; optional enqueue_web
           Daemon job crawl:URL   TUI /crawl URL
  Web gate still: board -> hands.web.fetch -> 0x-WEB | Tx-REJECT
  RAG:     nova/rag.py      word-weight search + small-model INCLUDE/EXCLUDE gate
           TUI /rag QUERY   (clears noise before big prompt; facts stay as written)
  Base glass knowledge: deepen Textual + Qt/PySide docs first.
  Diary:   C:\Users\wuchy\Documents\NOVA\GrokBot.log.ai  (append-only orientation)

  Known jobs (additions): openclaw-status qwen-status workforce claw-ping claw-run
                          crawl:URL  camsee:N  mail
  Slash additions: /claw /qwen /snap /chamber /crawl /rag

