# Avatar lip-sync pipeline — steward plan (council topic)

Topic: slice pre-made silent avatar MP4s → vision-label mouth states → mouth blanks → Pocket TTS timed speak face.

## A_SEATS
- steward: Agree — inventory-first; use thumb clips; CPU vision on OG; stitch on TUF or OG.
- code: Agree — ffmpeg + moondream/qwen3-vl classify + Python stitcher; no new full CGI.
- small: Agree — start with 8 mouth classes; polish later.

## B_VISION
Prefer **moondream** first on OG (lighter). Escalate hard cases to **qwen3-vl:2b**. Batch offline overnight; cache JSON labels next to frames.

## C_TAXONOMY (mouth blanks)
1 closed  2 open_small  3 open_mid  4 open_wide  5 round_O  6 smile_closed  7 smile_open  8 teeth
ffmpeg: extract 2–4 fps stills OR scene-change cuts; crop mouth ROI after a one-time face box (vision or fixed ROI from sample frame).

## D_SYNC
TTS wav duration T seconds → N = ceil(T * fps_blank). Map phoneme/energy envelope OR simple amplitude bins from wav to class sequence; hold each blank 2–4 frames; crossfade optional.

## E_STEPS
- P0: catalog mp4s (avatar_display already) PROOF=clip list
- P1: ffmpeg extract frames for 3 pilot clips → data/artifacts/avatar_frames/ PROOF=counts
- P2: OG job vision_label frames → JSON classes PROOF=sha of labels
- P3: build blanks library folders by class PROOF=tree
- P4: stitch demo: TTS sentence + blank sequence → preview mp4 PROOF=output file

## F_RISKS
Thermal on OG during vision batches; disk growth; weak sync if amplitude-only; keep paint/ComfyUI PARKED during heavy Ollama.

Zulu steward note written alongside live phi3 council job.
