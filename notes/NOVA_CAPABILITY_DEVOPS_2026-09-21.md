NOVA Command (glass) vs metal — capability, data, devops
========================================================
Steward: Grok Bot | Operator: Michael S. Wuchevich | 2026-09-21
Glass: https://ivory-jolly-sapphire-lark.grok.me/

A. WORK FLOW WITH GROK BOT — do we have the five cuts now?
----------------------------------------------------------
1. Auto-drain ingest_pipe in maintain     WIRED (sched.maintain -> crawl.drain_temps_through_pipe)
2. Promote-after-verdict policy           WIRED (chamber.AUTO_PROMOTE_RAG=True per motion)
3. Pocket TTS play hooks / employee voices WIRED (normalize+winsound; speak_employee; SEATS expanded;
                                               office.sync_voices_from_pocket; whistle uses seat voice)
4. WHI lag whistle L0                     WIRED (whistle alerts if newest fact >5min old, sentinel voice)
5. Aurelius PROOF-before-DONE             WIRED (nova/proof.py + leash.openclaw_run rejects DONE without matching bytes)

Honest gaps still inside those cuts:
- Employee *models* in office still name pruned jackets (nova-sentinel, llama3:8b, gemma2:2b) — voices fixed, brains stale.
- Auto-drain uses chronicler+qwen3:8b only (not full A-F mask rotation yet).
- PROOF gate matches exact byte sizes in nova-out; placeholder PROOF lines still fail (good).
- Term/GUI peel paths should call speak_employee — peel->speak exists; audit any bypass of _play.

B. CAPABILITY VS NOVA COMMAND SITE (L0–L6)
------------------------------------------
L0 Awareness     PARTIAL — holmes/cam/whistle exist; glass "probes across castle nodes" not full LAN/NAS orchestra.
L1 Fact store    STRONG  — SQLite facts ~1.2k+, WHI classify+indexes, provenance headers on pipe ingest.
L2 Orchestra     PARTIAL — chamber MoE claw+code+brief; not full sealed-packet contrast UI.
L3 Logical core  THIN    — bounded recursive angles / flourishing fences mostly glass doctrine, not metal loop.
L4 Gated action  PARTIAL — HIL for WA; queue/approve exists; not continuous remediation orchestra.
L5 Memory palace STRONG+ — WHI, RAG live gate, ingest_pipe, promote policy; saturation plan still prune-first.
L6 Embodiment    PARTIAL — PySide6 GUI + TUI + Pocket TTS + cam; no glass-parity dashboard; STT missing.

Glass scheduler (Holmes, palace prune, weather, idle whistle/refine, utilize scout, symbiosis, paper market):
  Metal has holmes/maintain/whistle/cam — NOT weather, idle refine, utilize scout, symbiosis, paper market as live jobs.

C. DATA HANDLING & ARTIFACT STORAGE (meditation)
------------------------------------------------
Today:
  data/NOVA.db     — facts, chunks, jobs, employees, packets, conversations (single SQLite; never wipe)
  data/artifacts/  — wav, cam stills, web_last.txt, vision/, codesum, etc. (files on disk, cites in DB)
  STAGING/         — steward paper trail, councils, matrices (not always promoted to live RAG)
  ~/.openclaw/workspace/nova-out/ — Aurelius write path; steward pulls

What works: append-only diary; WHI wings; live vs temp vs cleared chunks; provenance on pipe.
What's fragile:
  - Artifact files can orphan if facts deleted; no GC linking file↔fact
  - Temps can pile if drain fails / Ollama down
  - Glass "immutable snapshots / sharded" vs metal single DB — sharding is future council cut
  - No retention policy for artifacts/tts_*.wav growth
  - Council JSON in STAGING duplicated into DB only when promote runs

Ideal: every artifact has WHI cite + content_hash; GC job prunes unreferenced files; chunks.db attach if saturation.

D. DEVOPS PLAN TO CLOSE GAPS (ordered)
--------------------------------------
P0 (this week, metal):
  1. Refresh office employee models to live Ollama tags (drop jacket names).
  2. Wire speak_employee into TUI peel + GUI speak paths (audit).
  3. Daemon job: artifact GC + temp chunk age clear after drain.
  4. Declarative cron.txt / job table docs matching glass scheduler names where we keep them.

P1 (next):
  5. STT assessment council (self-hosted, Pocket TTS already chosen for out).
  6. L0 awareness pack: LAN/NAS probes from D:\pg\ai heritage (holmes lineage).
  7. Settlement 10-section steward brief from live RAG; geology round.
  8. WA QR + lean email plugin (HIL).

P2 (glass parity / later):
  9. Dashboard widgets (facts/queue/GPU) reading live DB — not marketing stubs.
 10. Weather / idle refine / paper market only if purpose-fit (daemon council).
 11. DB attach split by WHI if >~1000 crawls hurts tick latency.
 12. Frost Shield / FRONTINUS ingest tracks as dedicated palace wings.

E. GROK BOT WORK FLOW WITH YOU
------------------------------
I act as steward: patch metal, run councils, leash Aurelius, diary stamp, never wipe DB.
You approve outbound (WA/email), QR, and consequential policy.
Aurelius writes nova-out with PROOF; I pull and promote.
Pocket TTS only for voice. A-F masks = handling stages for knowledge.
