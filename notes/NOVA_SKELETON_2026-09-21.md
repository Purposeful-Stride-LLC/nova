# NOVA system skeleton (quick audit)
2026-09-21 02:25 local

## Spine
Operator (Michael) -> Steward (Grok Bot) -> fieldkit ova/\ on TUF
Palace: data/NOVA.db (facts~1450, chunks~213, packets~113) + data/artifacts (~204 files)
WHI taxonomy on facts/chunks; indexes via whi.ensure_indexes(con) in maintain

## Layers
L0 code-only (no LLM): holmes + watson + awareness probes | whistle lag | cam stills | homestead.cycle
L1 voice: Pocket TTS anna/:8000 only (speak / speak_employee)
L1 ear: ear_stt PTT HIL, faster-whisper CPU (not always-on)
L2 pets (leashed): Aurelius Nova (OpenClaw) | komodo Qwen Code | chamber MoE (claw/code/brief)
L2 see: moondream via senses.describe (VLM) — NOT paint
L3 ingest: crawl -> matrix -> ingest_pipe -> A-F masks -> facts/chunks; maintain auto-drain
L3 channels: msg WhatsApp HIL (QR stuck); imap plugin installed, no mailbox yet
Jobs enabled: holmes@300s, maintain@1d, whistle@900s, cam:0@900s, homestead-cycle@3600s

## Can / cannot (honest)
CAN: speak, write (diary/poetry via seats), see (moondream), map metal (Holmes/Watson), council, crawl, stamp WHI
CANNOT yet: paint (no Diffusers / no Qwen-Image), reliable WA link, email send, always-on STT (by design)

## GPU reality (this audit)
RTX 5050 Laptop ~8GB; probe showed ~6.4GB used / ~1.5GB free while Ollama pets warm — paint must not jam into Ollama seats.
