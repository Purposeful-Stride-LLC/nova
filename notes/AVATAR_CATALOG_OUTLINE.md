# AVATAR_CATALOG_OUTLINE.md
Root: D:\pg\ai\nova-ai\agents\avatar

Per mp4 capture: fps/frames/duration, kind (emotion/event/grok_raw), mood_tags from name + vision,
transitions via panel frame-diff, mouth_activity low/med/high, best_idle / best_for_events,
sample panels on disk, sparse moondream notes, Ax-AVATAR fact.

Job avatar-catalog: enumerate -> hash skip -> cv2 panels -> diff -> optional moondream if VRAM free
-> AVATAR_CATALOG.md + avatar_catalog.json -> put_fact. Mutex vs Aurelius heavy runs.
First slice: Btyping, Blaughing, Bangry, Bquiet, Breflective.
