# NOVA pet training playbook
Steward = dog trainer. Pets obey leashes, PROOF, and HIL.
Operator: Michael S. Wuchevich | 2026-09-21

## Roster
| Pet | Role | Leash | Obedience rules |
|-----|------|-------|-----------------|
| Aurelius Nova (lobster / OpenClaw) | Messenger, browser, STEPs | `leash.openclaw_run` → nova-out | PROOF: bytes=N or proof-reject; no WA/email without HIL; write nova-out only |
| Qwen Code (komodo) | Code STRUCTURE valet | `leash.qwen_run` / `hands.qwen` | Propose only until HIL; no silent file writes |
| Holmes | L0 metal probes | `holmes.sweep` / job `holmes` | Code only — no LLM; stamps Ax-HOLMES |
| Watson | Tree/map of key roots | called by Holmes | Code only; watson_tree.txt + Ax-WATSON |
| Pocket TTS (anna+) | Speak | `pocket.speak` / `speak_employee` | Pocket only; normalize wav then winsound; report play ok |
| Office employees | Masked seats | office + pocket.SEATS | Voice from SEATS; models = live Ollama tags |
| Chamber (claw/code/brief) | MoE council | `chamber.session_motions` | Auto-promote RAG after motion |
| Ingest pipe / spider | Web jack-in | crawl + ingest_pipe + maintain drain | Matrix weigh; provenance header; A-F masks |

## Training drills (daily / on tick)
1. `sched.tick()` — holmes(+watson), maintain(drain+tts_gc), whistle(lag), cam:0, homestead-cycle (hourly)
2. Mail Aurelius a BASIC STEP with PROOF rule; reject DONE without bytes
3. Ask komodo STRUCTURE on one path before any forge write
4. `/tts` or speak_employee — confirm play dict ok
5. homestead.cycle — needs list → pick one jack-in wire

## Never
- Wipe NOVA.db
- Melt thumb shards into fieldkit blindly
- Ollama TTS instead of Pocket
- Treat Ack as Done

## Recall cues for steward
"Walk the lobster" = OpenClaw STEP
"Komodo" = qwen_run
"Holmes and Watson" = L0 sweep + tree
"Queue is law" = jobs table + HIL
