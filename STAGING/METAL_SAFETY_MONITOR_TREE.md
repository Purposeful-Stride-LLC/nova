# Metal safety monitoring decision tree
Steward draft | 2026-09-21 02:17 local
Goal: protect TUF metal while sharing one NVIDIA GPU. Prefer L0 code over LLM tokens.

## L0 always-on (code only - no GPU)

tick / jobs
- holmes (300s): probes + watson tree -> Ax-HOLMES / Ax-WATSON
  - FAIL probe? office.report severity>=2; steward alert; do NOT auto-reboot
- whistle (900s): WHI lag if newest fact >5min
  - LAG? Tx whistle; check maintain/drain stuck; no LLM chase
- cam:0 (900s): still only (no VLM unless camsee)
- homestead-cycle (3600s): needs list; jack-in only with HIL forge

## GPU / VRAM gate (shared card)

Before any LLM / whisper / VLM:
1. Is L0 enough? YES -> stay code-only
2. Is Claw/Aurelius mid-run? WAIT or STOP; then one-off nova CLI council (brief/small first)
3. STT ear_stt? CPU int8 only; approve=True PTT; never always-on
4. Chamber motion? claw/code/brief; AUTO_PROMOTE_RAG ok when free
5. VLM camsee? rare HIL; moondream when free

## Channel / outbound gate

WA / email / browser:
- linked + HIL approve? allow send/draft
- not linked / no creds? status only; QR / config
- PROOF missing on Aurelius DONE? proof-reject

## Thermal / process red

Holmes process/network/volume probe bad:
- disk full / D: missing -> stop homestead jack-in; alert
- ollama wedged -> do not stack models; restart ollama only with HIL
- pocket :8000 down -> speak fails soft; fix TTS not swap engine

## Decision summary
1. L0 first. 2. One GPU consumer at a time. 3. HIL for mic/mail/WA. 4. Never wipe NOVA.db.
