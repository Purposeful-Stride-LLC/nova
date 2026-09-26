# Avatar inventory
2026-09-21 03:01 local
Root: \D:\\pg\\ai\\nova-ai\\agents\\avatar
## Contents
- ~80+ mp4 clips (nova_* emotion/event + grok_video_* raws) + 3 jpgs
- Legacy Linux-oriented player: \ideo_player.py\ + \ideo_player.config  - OpenCV loop player; config paths still \/home/mike/pg/ai/...\ (Linux homestead)
  - frame_delay_ms=33 (~30 fps); playlist of emotion clips
- TUF has cv2 + PyAV; no moviepy/PIL yet (cv2 enough for panels)

## Emotion / event naming (examples)
Btyping, Blaughing, Bangry, Bquiet, codecomplete, newemail, morning, potentialproblem, ...

## Smoke
Extracted ~1 fps panels from nova_Btyping.mp4 → fieldkit \data/artifacts/avatar_panels/smoke_Btyping/