# Staging vs integration - next stage plan
2026-09-21 02:17 local

## Definitions (NOVA fieldkit)
- Staging: specs, councils, seeds, playbooks, sims in STAGING/ and box mirrors. May be wrong; never mutate live NOVA.db from staging alone.
- Integration: live modules + jobs + palace (nova/*.py, data/NOVA.db, jobs table). PROOF + smoke before enable; HIL for outbound.
- Thumb shards: heritage D:/pg/ai - jack-in via homestead; wire, do not melt.

## This stage (done / in flight)
- P1 channels: WA QR launched (operator scan); IMAP plugin installed, creds pending
- ear_stt module + CPU deps; smoke_offline ok
- L0 Holmes/Watson, homestead-cycle, five daemon cuts
- Pets playbook + metal safety tree
- WHI indexes ensured (facts + chunks)

## Next stage (propose)
1. WA linked smoke - one allowlist DM with approve=True
2. IMAP config - dedicated mailbox + HIL draft/send wrapper
3. ear_stt HIL pilot - one approve=True listen on TUF mic; keep CPU
4. Settlement 10-section brief from live RAG when GPU free
5. Integration test pack (below)

## Testing needed before integration green
| Test | Pass criteria |
|------|----------------|
| Import smoke | from nova import ear_stt, homestead, holmes, whi, msg |
| Job smoke | sched.run_named holmes, maintain, whistle, homestead-cycle, cam:0 |
| WHI index | idx_facts_whi exists; prefix lookup works |
| PROOF | Aurelius DONE without bytes -> reject |
| TTS | speak anna play ok after normalize |
| WA | status linked; draft ok; send only approve=True |
| Email | plugin loaded; send blocked without HIL + config |
| STT | smoke_offline ok; listen requires approve |
| GPU etiquette | no concurrent claw+whisper+vlm |
| Backup | copy NOVA.db before any schema migrate |

## Rollback
- Disable job in db; leave module in place
- Plugin: openclaw plugins disable imap
- Never drop facts/chunks to fix WHI
