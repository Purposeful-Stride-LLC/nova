# STEP — OpenClaw development drop (Aurelius / main)
STEP_ID: OPENCLAW_DEV_DROP_2026-09-26R1
Zulu intent: 2026-09-26T16:00:00Z | Steward: Varro | Metal: TUF
Aligned after live review 2026-09-26 ~10:55 CDT (do not use the pre-review draft).

## Mission
One steward-authorized development drop. Stay GPU-polite. Leave OG tentacle WHI drain alone.
Obey clawbotinstructions: finish this ONE STEP, report DONE/FILES/PROOF/NEXT (≤5 lines human summary + artifacts), then wait.

## Live baseline (Varro measured 2026-09-26 ~10:55 CDT)
- OpenClaw gateway: **running** pid 34548, Listening 127.0.0.1:18789, Probe ok, Dashboard HTTP **200**, CLI 2026.9.4
- Fieldkit: `Documents\NOVA\NOVA_fieldkit_v1_4` present
- ComfyUI + `NOVA_PAINT\cold_start.bat` / `cold_stop.bat` at `Projects\ComfyUI\NOVA_PAINT`
- Port **8188** was **down** (paint PARKED)
- GPU: RTX 5050 Laptop, **~7049/8151 MiB used**, **~862 MiB free**, util 0% — two `ollama\llama-server.exe` hold VRAM
- `STAGING/gui_art/` empty / missing winners
- Avatar residue already present: `nova-out/REPORT_AVATAR_PYTHON_BUILD.md`, `STEP_AVATAR_REISSUE.txt`, lip-sync council RESULT + steward plan under `STAGING/acquisition/`
- OpenClaw workspace: `%USERPROFILE%\.openclaw\workspace` (Aurelius Nova); prior avatar STEPs already copied there
- Hub queue: `data/queue/waiting/` has stale `council-avatar-viseme-20260922T115601Z.json` (kind=`ollama_gen`) — **ignore / do not run** as part of this drop
- Daily OG WHI haul routine: **paused** by steward — no palace promote
- Day progression on disk still dated 2026-09-22 — refresh after this drop

## Preconditions (fail soft)
1. TUF local tools reachable.
2. Gateway still listening (re-probe; if dead, note and stop after Phase A report).
3. Do **not** kill Ollama, Steam, or other GPU holders unless steward explicitly says unload.
4. Do **not** SSH-kill OG drain / tentacle.

## Phase A — Light checksum (always)
1. `openclaw gateway status` → Runtime pid, Listening, Probe, versions.
2. HTTP GET `http://127.0.0.1:18789/` expect 200.
3. Append one line to `Documents\NOVA\GrokBot.log.ai` (append only):
   `YYYY-MM-DDTHH:mm:ssZ claw_devdrop checksum gateway=ok|fail dash=HTTP_n pid=... vram_free_mib=...`
4. Write `STAGING/REPORT_CLAW_CHECKSUM_2026-09-26.md` (short: status, VRAM free, avatar residue paths, blockers).
5. Do **not** run full midnight palace checksum.

## Phase B — Paint sidecar (HARD VRAM GATE)
Policy from `STAGING/AX_COMFYUI_SIDECAR.md` + day progression: paint stays **PARKED** while Ollama shares the RTX.

1. Run `nvidia-smi` / query free MiB.
2. **If free VRAM < 4096 MiB:** SKIP paint. Write `STAGING/REPORT_COMFYUI_GUI_SMOKE_2026-09-26.md` with blocked reason + process list (ollama llama-server). Do **not** start Comfy. Do **not** stop Ollama. Continue Phase C.
3. **Only if free ≥ 4096 MiB:**
   - Create `STAGING/gui_art/` if missing
   - `NOVA_PAINT\cold_start.bat` (listen 127.0.0.1:8188)
   - Wait ≤3 min for `http://127.0.0.1:8188/system_stats` = 200
   - Mint 2–4 polite SD1.5 PNGs 768x512 ~20 steps cfg~7:
     dark homestead night | lunar command deck | frostshield glass | optional warm forge
   - Save as `STAGING/gui_art/nova_gui_bg_*_2026-09-26.png`
   - `NOVA_PAINT\cold_stop.bat`
   - Report paths + prompts + VRAM before/after in the smoke report
4. If Comfy fails to bind: capture `NOVA_PAINT\comfy_start.log*`, stop listeners on 8188, continue Phase C.

## Phase C — Avatar lane status only
Already forged / planned — do **not** reissue mega avatar STEPs or start CPU councils on TUF.

1. Confirm existence (paths only):
   - `nova/avatar_display.py`
   - `nova-out/REPORT_AVATAR_PYTHON_BUILD.md`
   - `STAGING/acquisition/COUNCIL_STEWARD_AVATAR_LIPSYNC.md`
   - `STAGING/acquisition/COUNCIL_RESULT_AVATAR_LIPSYNC.md`
2. Optional one smoke if free and CPU-only: `python nova\avatar_display.py smoke_test` from fieldkit root (prefer `C:\Python314\python.exe` if present).
3. Note whether `nova/avatar_viseme.py` exists (likely missing — status only, no forge unless steward asks).
4. Avatar ≠ paint. No faces into ComfyUI.
5. Ignore the stale waiting `council-avatar-viseme-*.json` job.

## Phase D — Palace / WHI posture (hub only)
1. No bulk OG ingest / promote while daily haul is paused.
2. Optional one peek only if SSH `og-ubuntu` works: packets count + OG `queue/waiting` size — write numbers into checksum report. No promote.
3. Mesh reminder: beacon UDP **41776** + job TCP **41777** (see `STAGING/NOVA_MESH_CHANNEL.md`). Do not invent new ports.

## Phase E — Close
1. `nvidia-smi` — confirm Comfy not left running; Ollama may still hold VRAM (expected if Phase B skipped).
2. Write/update `STAGING/DAY_PROGRESSION_2026-09-26.md` with this drop outcome (do not delete 2026-09-22 file).
3. Steward summary artifacts under `STAGING/` + optional copy of reports into `%USERPROFILE%\.openclaw\workspace\nova-out\`.

## Out of scope (still HOLD)
- Bot template / Grok competition share
- Gemini wiring
- Qwen-Image heavy pulls / HF downloads
- Unpausing daily OG WHI haul
- Killing OG tentacle drain
- Full midnight palace checksum
- Unloading Ollama without steward

## Success
- Checksum report written
- Phase B either ≥2 PNGs in `STAGING/gui_art/` **or** explicit VRAM-blocked smoke report (expected given ~0.9 GiB free)
- Comfy not left running
- OG drain untouched
- Report format:
  DONE: <one line>
  FILES: <paths>
  PROOF: tree + sha256 of new reports (and PNGs if any)
  NEXT: STOP (or steward-named follow-up)
