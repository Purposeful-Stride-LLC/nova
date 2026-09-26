# OG node WHI + awareness — 2026-09-22

- DB: ~/pg/nova-tentacle/whi/NOVA_NODE.db
- Queue: 200 subjects waiting; drain via whi_drain.py (CPU ollama → packets.status=raw)
- Sync doctrine: keep raw packets on OG; schedule haul to TUF for review against palace WHI before promote
- TTS: pocket_tts TTSModel + eponine; paplay works; reports in outbox + STAGING/acquisition/OG_HAUL_2026-09-22
