# NOVA Missing-Steps Build Order
Steward lock: 2026-09-22 06:02 CDT
Scope: fold STAGING → live jobs without GPU thrash. Owners: steward / Komodo (Qwen) / Claw (OpenClaw/Aurelius) / Cassius / tentacle.
GPU budget default: prefer `qwen2:0.5b` or CPU; unload with keep_alive=0; no long councils unless STEWARD_RUN=1.

## Phase map (A→I)

| ID | Phase | Owner(s) | Success PROOF | GPU budget |
|----|-------|----------|---------------|------------|
| **A** | Beacon/tentacle always-on (lid close, no sleep, systemd, queue) | steward + Cassius + tentacle | OG beacons on UDP 41776; tentacle systemd active; job inbox on 41777 accepts envelope; lid-closed stays awake | none (CPU only) |
| **B** | Mail/job schema + waiting queue on hub+node | steward + Claw | `HEARTHBEAT_MAIL_JOB_SCHEMA.md` live; `data/queue/{waiting,running,done,failed}/` exist; one smoke job round-trips with tree+sha256 PROOF | none |
| **C** | Education seed series (initial RAG population) | Komodo drafts → Claw forge → steward promote | Seed URL list + ingest_pipe dry-run packet; ≥N Ax-EDU facts after steward go | small: one seat, keep_alive=0 |
| **D** | WHI gap scout → search → ingest_pipe loop (scheduled) | Claw + tentacle + steward HIL | Job `whi-gap-scout` (disabled default) writes agenda; ingest_pipe review queue; steward promote only | thermal-gated; 0.5b scout OK |
| **E** | Leash forge path Komodo→Claw fold STAGING→live | Komodo + Claw + steward | LEASH workflow documented; STEPs under STAGING/steps; forge/proof path returns bytes/tree/checksums | Komodo code model only when drafting; Claw execute short |
| **F** | Paper markets module (design→skeleton→PROOF) | Komodo → Claw → steward | Design already in notes/PAPER_MARKETS.md; skeleton `nova/paper.py` stub + disabled jobs; PROOF = import + empty wallet table create | no LLM until steward enables paper-* |
| **G** | User-facing loops (HIL, ear, diary, GUI) | steward + Claw | HIL before external write; diary append works; ear/GUI clients of DB only | TTS anna :8000 polite |
| **H** | GitHub sync cadence | steward (Frontinus2) | Docs-only commits to Purposeful-Stride-LLC/nova; no secrets/db | none |
| **I** | Recursive council schedule (this package) | steward + chamber seats | COUNCIL_SERIES_SCHEDULE.md + `council-series` stub job writes next-topic only unless STEWARD_RUN=1 | **strict**: agenda-only by default |

## Dependency edges
A → B → (C ∥ D) → E → F → G; H continuous; I reviews A→H recursively (each council audits prior PROOF gaps).

## Exit criteria for “structure lock”
- Files in this STAGING package exist and are copied into `docs/` / `notes/` as appropriate.
- `data/queue/` present with README.
- `council-series` registered in forge as disabled / long-interval stub.
- Human DEVLOG section explains pets + mail for a non-dev reader.
- No passwords/tokens in palace text or these docs.

## First fire when steward says go
**Council A — Beacon Always-On** (see COUNCIL_SERIES_SCHEDULE.md). Agenda-only unless STEWARD_RUN=1.
