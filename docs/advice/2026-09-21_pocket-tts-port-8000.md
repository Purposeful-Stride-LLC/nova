# advice pocket tts port 8000 not 3000
Date: 2026-09-21
Pocket TTS serve listens on http://127.0.0.1:8000 (health + POST /tts). Kyutai pocket_tts CORS allow_origins includes http://localhost:3000 for their web demo — that is NOT the API listen port. NOVA must never point speak/serve_up at :3000.
GUI: if serve down, popup asks to activate; Yes -> start_serve_window() parallel console; No -> quiet. Daemon (python -m nova) stays separate in background.
