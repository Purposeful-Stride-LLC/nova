# Avatar vision catalog JOB (framed)

## Purpose
One video is transitions, poses, mouth phases, background shifts — not one tag.
Catalog so daemon picks clips intelligently and palace can RAG moods.

## Job name (proposed)
avatar-catalog — every 6h OR sched.run_named("avatar-catalog")
Worker: CPU panels, then optional moondream on 3-5 key panels when GPU free.

## Per-video fields
file, bytes, fps, frames, duration_s, resolution
kind: emotion | event | grok_raw | still
mood_tags (filename seed + vision)
transitions (panel diffs / VLM)
mouth_activity: low|med|high
best_idle, best_for_events
sample_panels paths
vision_notes
whi: Ax-AVATAR
zulu

## Must-do pipeline
1. Enumerate D:\pg\ai\nova-ai\agents\avatar\*.mp4
2. Skip if catalog hash fresh
3. cv2: metrics; panels at 0/25/50/75/100% (cap 8)
4. Frame-diff between panels -> transition_hint
5. If free VRAM high enough and policy allows: moondream on mid + high-diff panels only
6. Merge STAGING/AVATAR_CATALOG.md + data/artifacts/avatar_catalog.json
7. db.put_fact Ax-AVATAR
8. Abort if VRAM drops or Claw heavy run (mutex)

## First execute slice (when approved)
Five emotion clips only: Btyping, Blaughing, Bangry, Bquiet, Breflective — then overnight batch.
