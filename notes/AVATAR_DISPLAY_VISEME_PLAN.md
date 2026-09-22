# Avatar display + viseme stitch PLAN (pre-execute)
Status: PLANNING ONLY — do not ship full stitch yet.

## Product feel (daemon on glass)
- Small always-on-top avatar window (legacy video_player pattern) OR deck tile that embeds the same surface.
- Modes:
  1. Idle cycle — random calm clips (Bquiet, Breflective, morning, online)
  2. Event-driven — map office/daemon events to mood clip (newemail, codecomplete, potentialproblem, Bangry, Blaughing, ...)
  3. Speak-driven — Pocket TTS plays; mouth/timeline follows speech

## Theory (correct axis)
Video = ordered panels (FPS). Anime mouth protocol is visemes (JP vowels A/I/U/E/O + closed/rest).
Compile a timeline of pre-shot mouth/emotion samples at TTS cadence; stitch with short pauses for cutovers.
Silent picture clips + separate TTS wav = face without diffusion GPU.
Crude loop already possible: ear_stt (PTT) -> brief reply -> speak + play mood clip.

## Build order
L0 Player — Windows-path jack of video_player; play one clip by name; stop/pause API
L1 Event map — mood dictionary: event/WHI -> clip basename; idle RNG from allowlist
L2 TTS sync (crude) — speak() duration; play clip looped/trimmed to wav length (no viseme yet)
L3 Viseme stitch (refine) — vowel/phoneme rough align -> mouth panel sequence -> stitch or sequenced play
L4 STT dialogue — ear_stt.listen(approve=True) -> brief one-liner -> L2
L5 Catalog — vision job documents each video
L6 Future credits — Grok video/stills for missing covers; still no local diffusion face

## Viseme stitch (phase 2)
1. Mouth atlas from clips: closed, A, I, U, E, O
2. From TTS text or wav energy: rough vowel stream + pause marks
3. Timeline with pad gaps for scene change
4. Render via sequenced short plays OR cv2/ffmpeg concat silent mp4 under wav
5. Measure Pocket TTS wav duration; never assume FPS alone

## GPU etiquette
Panel extract + playback = CPU. Vision catalog = sparse moondream when VRAM free. No Qwen-Image for face.

## Glass to RPG
Same event->clip->TTS contract Cassius can copy into Projects RPG GUI.

## Execute gate
Approve L0+L1+L2 first. Viseme stitch is phase 2.
