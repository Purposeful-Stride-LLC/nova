# Review alignment — OpenClaw dev drop vs live NOVA (2026-09-26)

## What was outdated in the first STEP draft
1. Assumed paint could run after reconnect — **false**: Ollama holds ~7 GiB; free ~0.9 GiB; AX sidecar says PARK while Ollama shares GPU.
2. Implied avatar “continue forge” — **false**: avatar_display + lip-sync RESULT/steward plan already landed; reissue STEP already in workspace.
3. Day progression pointer was stale (only `DAY_PROGRESSION_2026-09-22.md`).
4. `gui_art` winners do not exist yet — empty.
5. Hub `data/queue/waiting` is not empty — stale `council-avatar-viseme` ollama_gen job must not be confused with this drop.
6. Clawbotinstructions require **one STEP** + DONE/FILES/PROOF/NEXT — multi-phase is a checklist inside one authorized STEP, not five separate forges.
7. Hearthbeat port text in some notes mixed UDP/UDP; live mesh doctrine is UDP 41776 + **TCP** 41777.

## What still holds
- Gateway healthy (pid/listening/probe/200) — Phase A is mostly confirm + log.
- Comfy tree + cold_start/stop present under Projects\ComfyUI\NOVA_PAINT.
- Daily haul paused — no promote.
- Leave OG drain alone.
- Mail path: workspace STEP + fieldkit STAGING/steps + nova-out + queue envelope `step.execute` → openclaw@local.

## Expected drop outcome today
Likely: A ok, **B blocked on VRAM**, C status-only, D peek optional, E day note. Paint unpark needs steward “unload Ollama / free GPU” first.
