# NOVA — Fieldkit v2.1

**Homestead AI that lives on your metal** — a local-first field kit with a mind-palace memory, leashed helpers, and human-in-the-loop gates for anything that leaves the machine.

> Copyright © 2026 Purposeful Stride LLC. All rights reserved. See [`LICENSE`](LICENSE).
> Org: [Purposeful-Stride-LLC](https://github.com/Purposeful-Stride-LLC)

## What's new in v2.1 (vs v2.0)

- **Chat:** one path for TUI and GUI (`nova/chat.py`); SELF/NOW context blocks first; read-only palace hunt (chat never writes the DB); guards against fake action claims.
- **GUI:** read-only operator console (single `mode=ro` DB connection), health strip, "What NOVA knows" and Proposals panels. Every action is routed to the daemon through the command inbox.
- **Scheduler v2:** job table with priority, GPU class, next run and backoff; one heavy GPU job at a time; file-based command inbox; `task-stimulus` job that only *proposes* tasks (HIL).
- **Gates:** network allowlist (empty = refuse), approve-gated URL drain, chat command scope + ack, fail-closed RAG judge, governor stays in dry-run (`enforce: false`).
- **Self-improve loop:** HIL only, with PROOF before DONE.
- **Disk:** retention config + dry-run report only (`python -m nova.disk report`).
- **Paths:** no hardcoded user paths — everything resolves relative to the install / `NOVA_HOME` (see `nova/paths.py`).
- **Tests:** `tests/` (v2.1 + GUI acceptance + 2.0 smoke).

## Layout

| Path | Role |
|---|---|
| `nova/` | Python package — scheduler, chat, gates, governor, ingest, TUI, GUI |
| `config.example/` | Example `gates.json` (empty allowlist) and `governor.json` (enforce off) |
| `docs/` | GATES, SCHEDULER, mail protocol, testing checklist |
| `tests/` | pytest suite |
| `tools/` | simulation harness |
| `START.txt`, `TUTORIAL.txt`, `DEVLOG.txt` | operator cards and dev journal |

**Not in this repo:** `data/` (live `NOVA.db`, logs, artifacts, commands inbox), `.env`, keys, media.

## Install

Python 3.10+ and a local [Ollama](https://ollama.com) endpoint (`127.0.0.1:11434`) for chat.

```bash
git clone https://github.com/Purposeful-Stride-LLC/nova.git
cd nova                       # the install folder (contains nova/)
python -m pip install -r requirements.txt
mkdir -p data/config
cp config.example/gates.json config.example/governor.json data/config/
```

Web access **refuses every host** until you add hosts to `net_allowlist` in `data/config/gates.json`.

## Run (from the install folder)

```bash
python -m nova          # daemon: scheduler, DB writes, approved commands
python -m nova.tui      # terminal face; /cmd list, /cmd approve ID
python -m nova.gui      # read-only console (PySide6)
```

On Windows, `START_NOVA.bat` / `START_GUI.bat` do the same relative to their own folder. Set `NOVA_HOME` to keep data elsewhere.

## Tests

```bash
python -m pytest -q tests
```

Tests needing Windows, Qt, Ollama or a scratch DB copy (`NOVA_SCRATCH_DB`) skip automatically.

## Security

See [`SECURITY.md`](SECURITY.md).

## Ownership & license

Proprietary, All Rights Reserved — see [`LICENSE`](LICENSE). Public visibility does not grant any license, patent or trademark rights.
