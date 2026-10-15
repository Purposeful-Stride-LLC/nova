================================================================================
NOVA FIELD KIT 2.1  -  what changed since 2.0 (read this first)
================================================================================
  Chat      one path for TUI/GUI (nova/chat.py): SELF/NOW blocks first, RULES,
            GRAMMAR_V2, read-only palace hunt (no DB writes from chat).
            Model qwen3:8b, num_ctx 8192, think:false. Code guards for speak
            tags, command ids, action claims and voice answers.
  GUI       read-only console: one mode=ro connection, cached media scan,
            health strip, WHAT NOVA KNOWS panel (exact SELF/NOW text),
            PROPOSALS panel. Every action goes to the daemon via the command
            inbox. Unimplemented controls are hidden.
  Scheduler job table with priority / GPU class / next run / backoff; one
            heavy GPU job at a time; command inbox; task-stimulus job.
            See docs/SCHEDULER.md.
  Gates     net allowlist (empty = refuse), approve-gated URL drain, chat
            command scope + ack, governor fail-closed when enforcing (enforce
            stays OFF), RAG judge fail-closed, no chamber auto-promote,
            self-improve loop with PROOF. See docs/GATES.md.
  Disk      retention CONFIG + dry-run report only (python -m nova.disk report).
  Paths     no hardcoded user paths; see nova/paths.py and
            data/config/paths.json (docs_root, thumb_ai, avatar_root,
            steward_log, watson_roots, openclaw_cli).
  Tests     python -m pytest -q tests   (set NOVA_SCRATCH_DB to a COPY of the
            DB for the GUI acceptance tests; QT_QPA_PLATFORM=offscreen).
            59 tests; Windows/Qt/Ollama/scratch-DB tests skip when absent.

================================================================================
NOVA FIELD KIT 2.1
Purposeful Stride LLC  /  metal face  /  Python 3.10+
================================================================================

WHAT THIS IS
  Local homestead agent. Daemon ticks jobs. TUI is the window; the GUI is a
  read-only console. Palace is SQLite under data/ (NEVER ship or overwrite
  that folder). Code overlay: copy nova/ only onto a live tree.

LAYOUT  (install folder = the folder that contains nova/)
  nova/              this package
  data/              LIVE, not in the repo. NOVA.db, artifacts/, logs,
                     config/ (gates.json, governor.json, paths.json), cmd/
  config.example/    example gates.json (empty allowlist), governor.json
  docs/              GATES.md SCHEDULER.md MAIL_PROTOCOL_TCP.md
                     AI_CODE_TESTING_CHECKLIST.md advice/
  tests/             pytest suite
  README.md / README.txt / START.txt / TEST.txt / TUTORIAL.md / TUTORIAL.txt
  DEVLOG.md / DEVLOG.txt / DEVLOG.ai / SECURITY.md / VERSION

START
  See START.txt. From the install folder:
  Window A:  python -m nova          daemon
  Window B:  python -m nova.tui      TUI (/help /tutorial /sched /cmd list)
  Optional:  python -m nova.gui      read-only console
  Optional:  python -m pocket_tts serve --port 8000

COPY RULE (iterations)
  Overlay nova/ + docs/ + top-level docs. Leave data/NOVA.db alone.

DEPENDENTS  (cite these; they are not bundled)
  Python 3.10+
  Ollama          127.0.0.1:11434; chat model qwen3:8b (num_ctx 8192)
  pocket-tts      Kyutai. serve on :8000 (optional voice)
  psutil, opencv-python-headless, pypdf   (requirements.txt)
  PySide6         GUI (optional)
  certifi         optional SSL for /web

SAFETY
  Chat proposes, the operator approves (/cmd approve ID), the daemon does.
  Network refuses every host until listed in net_allowlist. Governor and
  disk retention are dry-run. See SECURITY.md and docs/GATES.md.

HISTORY
  See DEVLOG.md (public chronicle) and DEVLOG.txt (detailed loop log).
================================================================================
