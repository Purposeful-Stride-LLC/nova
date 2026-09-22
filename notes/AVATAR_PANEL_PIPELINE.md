# Avatar panel pipeline (frames = digital panels)
2026-09-21 03:01 local

Yes: video is panels flashed in order (FPS). Same comic-strip idea, timed.

## Goal
Silent clip + Pocket TTS wav + mouth sync = Nova face **without** image-gen GPU.
Optional: vision (moondream) describes sparse panels for palace tags / RPG glass cues.

## Tools (Python, already in toolbox doctrine)
1. **cv2 / PyAV** — decode, sample panels (every N frames or 1/sec), write jpg
2. **moondream** (rare, HIL/GPU-free window) — describe panel → Tx-CAM / Ax-AVATAR fact
3. **Pocket TTS** — speak line → wav (normalize + winsound as now)
4. Legacy \ideo_player.py\ — jack paths to Windows; play mood clip while wav plays
5. Later: simple mouth overlay (opencv) driven by wav RMS / phoneme stub

## Logical order
mood/event select → extract sparse panels (CPU) → optional VLM on 1–3 key panels when GPU cold
→ pocket.speak(text) → play clip loop for wav duration → stamp Ax-AVATAR

## Do not
- Diffusion/paint for face
- VLM every frame (burns shared 8GB card)
- Rewrite Linux player — leash it, fix paths

## RPG / glass crossover
Same mood-clip + TTS pattern Cassius can mirror in Projects RPG GUI once glass on NOVA is clean.
