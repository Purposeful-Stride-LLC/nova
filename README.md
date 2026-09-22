# NOVA Field Kit

**Private** GitHub repository for **Purposeful Stride LLC**.

Local-first homestead agent: daemon + TUI/GUI, SQLite palace under `data/`
(never ship live DB or secrets). This tree is the organizationally correct
fieldkit package overlay — code, docs, and private steward notes.

## Privacy

- Org: `Purposeful-Stride-LLC`
- Visibility: **private**
- Excludes: `data/NOVA.db`, `data/secrets/`, artifacts/wav/bin, zips, tokens, `.env`

## Layout

```
README.md          this file
.gitignore
VERSION
requirements.txt
START.txt START_GUI.bat START_NOVA.bat
TUTORIAL.txt TEST.txt
DEVLOG.txt DEVLOG.ai
nova/              Python package
docs/              product/ops docs
notes/             private steward/council RAG backup (from STAGING/)
nova-out/          small curated outputs
ascii/brand/       brand images (no boot.wav)
data/              runtime placeholder (.gitkeep only in git)
```

## Start (local)

```
cd to the folder that contains nova/
Window A:  python -m nova
Window B:  python -m nova.tui
Optional:  python -m nova.gui
```

See `START.txt`, `TUTORIAL.txt`, and `requirements.txt`.

## Copy rule

Overlay `nova/` + docs onto a live homestead. Leave `data/NOVA.db` alone so
PDF / web / history rows survive.

---

## Field notes (from README.txt)

```
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
```
