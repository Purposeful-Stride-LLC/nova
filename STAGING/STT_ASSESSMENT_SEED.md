# STT assessment (self-hosted, resource-constrained) — seed for council
Date: 2026-09-21
Constraint: local Ollama + Python on TUF (8GB VRAM class); Pocket TTS already chosen for OUT.

## Need
Speech-to-text for blind/STT users and hands-free steward; pair with Pocket TTS out.

## Candidates (lean review)
1) **faster-whisper** (CTranslate2) — strong offline, CPU or GPU; Python-friendly; good default
2) **openai-whisper** vanilla — heavier; worse fit for 8GB if large models
3) **Vosk** — very light CPU; weaker accuracy
4) **Windows.Media.SpeechRecognition** — OS-native; privacy/cloud quirks; less portable
5) **OpenClaw / Ollama audio plugs** — only if already local and HIL; do not assume

## Recommendation (steward)
Pilot **faster-whisper small/base.en** on CPU first (or tiny GPU), mic via sounddevice/pyaudio,
NOVA wrapper `nova/ear_stt.py` writing Tx-EAR facts + wav artifact — mirror cam:0 pattern.
Council should Confirm/Amend before install.

## Non-goals
Cloud STT; replacing Pocket TTS; always-on eavesdrop without HIL cue word.
