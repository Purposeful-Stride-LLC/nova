# Day progression — 2026-09-22 (Varro)

## Claw / Aurelius
- Gateway was zombie (process up, port dead). Hard-cleared locks + task restart.
- Dashboard now **HTTP 200** at http://127.0.0.1:18789/ — Listening 127.0.0.1:18789, probe ok (pid 26512).
- Avatar STEP reissued: `nova-out/STEP_AVATAR_REISSUE.txt` (+ workspace copy); agent re-dispatched.

## OG tentacle (192.168.0.76)
- WHI sqlite live: `~/pg/nova-tentacle/whi/NOVA_NODE.db` (tables packets, jobs)
- **200** `research_packet` jobs in `queue/waiting`
- `whi_drain.py` started (batches of 5, cheap `qwen:0.5b`, 8s thermal break) → packets + outbox `DRAIN_BATCH_*.json`
- Python: system 3.10; stack includes fastapi, beautifulsoup4, torch, ollama, **pocket-tts 1.1.1**, piper-tts
- Pocket TTS awareness: generated + **paplay** played `outbox/awareness_smoke.wav` (voice eponine; anna needs HF accept). Haul on TUF under `STAGING/acquisition/OG_HAUL_2026-09-22/`
- No HTTP TTS server on :8000 yet — library/CLI path works; FastAPI wrap later if wanted

## Plan next (queued doctrine)
1. Let OG drain subjects into raw sqlite packets while CPU is free
2. Timed ship of packet blocks → TUF for score/number vs palace WHI schema (docs_ingest / hexclass / 0x-DOC)
3. PDF/ebook scan both boxes → quality summaries → WHI index (already documented in NOVA)
4. Keep ComfyUI paint **PARKED** while Ollama shares TUF GPU
5. Avatar lip-sync continue on Aurelius after STEP lands

## Also shipped today (context)
GitHub nova+AiTutor, TCP hearthbeat 41776/41777, acquisition doctrine, paint park + ComfyUI sidecar, avatar_display forge, OG CPU councils.
