# Leash Workflow: Komodo (Qwen) → Claw (OpenClaw / Aurelius)
Updated: 2026-09-22 06:02 CDT
Intent: **make-it-so** with PROOF. Steward promotes. WHI/DEVLOG record.

## Roles
| Pet | Mask / seat | Job |
|-----|-------------|-----|
| **Komodo** | qwen@local / Qwen Code | Draft code, STEPs, patches under STAGING or nova-out only |
| **Aurelius / Claw** | openclaw@local | Forge/integrate: apply STEPs, return tree+sha256 PROOF |
| **Steward** | human HIL | Review PROOF → promote STAGING → `nova/` live |
| **WHI** | palace facts | Ax-* accept / Tx-* reject or temp |

## Make-it-so sequence
1. **Steward** posts packet kind=`task` dest=`qwen@local` with ONE STEP id (or files this workflow).
2. **Komodo** drafts: code or STEP template → writes under `STAGING/` or `nova-out/` (never wipe `data/NOVA.db`).
3. **Komodo** returns draft PROOF (bytes) via mail to `brief@local` / steward.
4. **Steward** (or auto if tagged) handoff kind=`task` dest=`openclaw@local`: forge STEP — integrate draft, run checks.
5. **Claw** executes forge: copy/patch into review path, compute **tree listing + sha256** of touched files, optional import smoke.
6. **Claw** returns result envelope (`HEARTHBEAT_MAIL_JOB_SCHEMA.md`) with `proof.tree` + `proof.sha256`.
7. **Steward** promotes: move approved overlay into `nova\`, append DEVLOG, stamp Ax-FORGE / Ax-CLAW.
8. **WHI**: reject path stays Tx-*; chamber temps cleared after judgment.

## PROOF minimum (non-negotiable)
```
DONE: <one line>
FILES: <paths>
PROOF: bytes=<n> tree=<count> sha256=<first16>…
NEXT: <id or STOP>
```

## Current code vs intended — PATCH list
Live modules today (`nova/claw.py`, `nova/leash.py`, `nova/forge.py`):
- `claw.py` — HTTP door status/ask only; **no forge/PROOF helper**
- `leash.py` — status + `openclaw_run` + `handoff`; **no tree/sha256 proof bundler**
- `forge.py` — job catalog only; **no STAGING→live fold**
- `sched.py` — `claw-run` drains one openclaw task; **no leash.forge verb**

### PATCH list (templates for Claw later — do not thrash GPU now)
| ID | Target | Change |
|----|--------|--------|
| P1 | `nova/leash.py` | Add `proof_tree(paths) -> {tree, sha256, bytes_total}` |
| P2 | `nova/claw.py` or `nova/forge.py` | Add `forge_step(step_path) -> result envelope` reading STAGING/steps |
| P3 | `nova/sched.py` | Job key `leash-forge` / `council-series` (stub landed) |
| P4 | `nova/office.py` | Optional status `waiting` alias docs; keep queued as law |
| P5 | tentacle | Accept envelope verb `leash.forge` / `step.execute` on 41777 |

STEPs for P1–P5 live under `STAGING/steps/` as Claw-executable templates.
