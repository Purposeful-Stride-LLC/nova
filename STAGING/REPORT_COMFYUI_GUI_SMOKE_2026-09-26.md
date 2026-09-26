# REPORT_COMFYUI_GUI_SMOKE_2026-09-26 (updated)
Zulu: 2026-09-26T16:14:43Z
Status: **IMAGES MINTED** via Diffusers fallback (Comfy :8188 did not stay up)

## Comfy attempt
- cold_start launched; crashed earlier on AppLocker blocking scipy _highs_options
- sd.py audio_vae stub applied (backup .bak_gui_mint_20260926); process still failed to serve 8188 this session

## Diffusers success
- Checkpoint: Projects\\ComfyUI\\models\\checkpoints\\v1-5-pruned-emaonly.safetensors
- Script: STAGING/mint_gui_diffusers.py
- Outputs: 4 PNGs under STAGING/gui_art/

## Music
- 5 WAVs under STAGING/gui_music/ via mint_gui_assets.mint_music()

## Human report
STAGING/REPORT_GUI_ART_MUSIC_HOWTO_2026-09-26.md
