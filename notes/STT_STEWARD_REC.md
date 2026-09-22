# STT steward lean recommendation (2026-09-21)
Council: 20260921T0654-50c71291 — S1/S2/S3 all Agree (claw/code/brief).

Ship next:
1. Pilot `faster-whisper` `small` or `base.en` on CPU first.
2. Push-to-talk or cue-word only (HIL) — no always-on mic.
3. Wire `nova/ear_stt.py` like `cam:0`: gated capture → wav artifact + Tx-EAR fact; Pocket TTS stays OUT only.

Do not: cloud STT, Ollama-as-mic, silent eavesdrop.
