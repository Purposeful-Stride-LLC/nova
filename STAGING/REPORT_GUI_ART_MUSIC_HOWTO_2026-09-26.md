# NOVA GUI backgrounds + music — human how-to and wiring plan
Date: 2026-09-26 | Author: Varro (steward) | Metal: TUF

## What was minted today

### Backgrounds (4 PNGs, 768x512, SD1.5)
Folder: Documents\NOVA\NOVA_fieldkit_v1_4\STAGING\gui_art

| File | Theme |
|------|-------|
| 
ova_gui_bg_dark_homestead_2026-09-26.png | dark homestead night |
| 
ova_gui_bg_lunar_command_2026-09-26.png | lunar command deck |
| 
ova_gui_bg_frostshield_glass_2026-09-26.png | frostshield glass |
| 
ova_gui_bg_warm_forge_2026-09-26.png | warm forge embers |

### Music beds (5 WAVs, mono 44.1 kHz)
Folder: Documents\NOVA\NOVA_fieldkit_v1_4\STAGING\gui_music

| File | Role |
|------|------|
| 
ova_gui_ambient_homestead_2026-09-26.wav | ~48s soft homestead drone |
| 
ova_gui_ambient_lunar_2026-09-26.wav | ~56s cool lunar bed |
| 
ova_gui_ambient_frostshield_2026-09-26.wav | ~52s icy glass bed |
| 
ova_gui_ambient_forge_2026-09-26.wav | ~44s warm forge bed |
| 
ova_gui_sting_focus_2026-09-26.wav | ~2.5s focus sting for tile click |

Manifest + checksums: STAGING/GUI_ASSETS_MANIFEST_2026-09-26.json

---

## How to do this manually (command prompts)

### A. Free the GPU (required on the 8 GB RTX 5050)
1. Quit heavy Ollama chats, or in PowerShell:
`powershell
ollama stop
# If models still hold VRAM:
Get-Process ollama*,llama-server -EA SilentlyContinue | Stop-Process -Force
nvidia-smi
# Want roughly >= 4 GB free before paint
`

### B. Preferred paint path — ComfyUI sidecar
ComfyUI lives at Projects\ComfyUI.
Cold helpers: NOVA_PAINT\cold_start.bat and cold_stop.bat.

`powershell
cd Projects\ComfyUI
.\NOVA_PAINT\cold_start.bat
# Browser: http://127.0.0.1:8188
# Workflow: Load Checkpoint (v1-5-pruned-emaonly.safetensors) -> CLIP encode pos/neg
#   -> Empty Latent 768x512 -> KSampler steps=20 cfg=7 euler -> VAE Decode -> Save Image
# Copy winners into fieldkit STAGING\gui_art\ with clear names
.\NOVA_PAINT\cold_stop.bat
`

**Known TUF snag (2026-09-26):** ComfyUI import crashes on
scipy.optimize._highs_options — Windows Application Control blocks that DLL.
A temporary stub was added in comfy\sd.py (backup comfy\sd.py.bak_gui_mint_20260926),
but Comfy still did not finish binding :8188 this session.

### C. Working paint path used today — Diffusers (same SD1.5 file)
`powershell
cd Projects\ComfyUI
.\.venv\Scripts\python.exe -m pip install "diffusers>=0.30" transformers accelerate
.\.venv\Scripts\python.exe Documents\NOVA\NOVA_fieldkit_v1_4\STAGING\mint_gui_diffusers.py
`
That script reads models\checkpoints\v1-5-pruned-emaonly.safetensors and writes the four PNGs into STAGING\gui_art\.

### D. GUI music beds (no GPU)
`powershell
C:\Python314\python.exe -c "import importlib.util; p=r'Documents\\NOVA\\NOVA_fieldkit_v1_4\\STAGING\\mint_gui_assets.py'; s=importlib.util.spec_from_file_location('m',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.mint_music()"
`
Or open STAGING\mint_gui_assets.py and call mint_music() only.
Play a bed:
`powershell
Start-Process explorer.exe Documents\NOVA\NOVA_fieldkit_v1_4\STAGING\gui_music
# Double-click a WAV, or:
Add-Type -AssemblyName presentationCore
\ = New-Object System.Windows.Media.MediaPlayer
\.Open([uri]'Documents\NOVA\NOVA_fieldkit_v1_4\STAGING\gui_music\nova_gui_ambient_lunar_2026-09-26.wav')
\.Play()
`

### E. After paint — park the card again
`powershell
# If Comfy was up:
Projects\ComfyUI\NOVA_PAINT\cold_stop.bat
nvidia-smi
# Restart Ollama / NOVA seats when you need LLM again
`

---

## Proposed method for NOVA to wire this in

### 1. Asset layout (promote after you like the art)
`
data/artifacts/gui/
  backgrounds/   <- PNGs (symlink or copy from STAGING/gui_art)
  music/         <- WAVs (from STAGING/gui_music)
  themes.json    <- maps theme id -> bg + ambient + sting
`

Example 	hemes.json:
`json
{
  "homestead": {"bg": "backgrounds/nova_gui_bg_dark_homestead_2026-09-26.png", "ambient": "music/nova_gui_ambient_homestead_2026-09-26.wav", "sting": "music/nova_gui_sting_focus_2026-09-26.wav"},
  "lunar": {"bg": "backgrounds/nova_gui_bg_lunar_command_2026-09-26.png", "ambient": "music/nova_gui_ambient_lunar_2026-09-26.wav", "sting": "music/nova_gui_sting_focus_2026-09-26.wav"},
  "frostshield": {"bg": "backgrounds/nova_gui_bg_frostshield_glass_2026-09-26.png", "ambient": "music/nova_gui_ambient_frostshield_2026-09-26.wav", "sting": "music/nova_gui_sting_focus_2026-09-26.wav"},
  "forge": {"bg": "backgrounds/nova_gui_bg_warm_forge_2026-09-26.png", "ambient": "music/nova_gui_ambient_forge_2026-09-26.wav", "sting": "music/nova_gui_sting_focus_2026-09-26.wav"}
}
`

### 2. Paint hand (already sketched in 
ova/hands/paint.py)
- Keep default **PARKED**.
- Unpark only with cold GPU: NOVA_PAINT=1 and NOVA_PAINT_BACKEND=diffusers (recommended on TUF until Comfy AppLocker is fixed) or comfyui.
- Gate on free VRAM (NOVA_PAINT_VRAM_MIN, today ~5500 MiB in code) + thermal band.
- generate(prompt) writes under data/artifacts/paint/ then steward can promote a winner into data/artifacts/gui/backgrounds/.
- Avatar lane stays untouched (mp4 + Pocket TTS).

### 3. GUI chrome (
ova/gui/app.py + console.qss)
- Set main window / stacked panel stylesheet ackground-image: url(...) from the active theme, with a dark translucent overlay so text stays readable (cosmic console look from the GUI enhancement notes).
- Prefer QPixmap scaled KeepAspectRatioByExpanding; do not stretch logos into the art.

### 4. Sonic layer (music aspect of the interface)
Palace already tracks **bites** (audio paths) in NOVA.db — treat GUI beds as first-class bites:
- On GUI start: load theme ambient with QMediaPlayer loop, volume low (~0.15–0.25).
- On deck tile focus / HIL approve: play the short sting once.
- Mute toggle in Staff or COP pane; persist preference in a small settings fact (Ax-GUI / gui-audio).
- Do **not** fight Pocket TTS :8000 — duck ambient 6–9 dB while anna speaks, restore after.

New thin module proposal (next forge STEP, not done today):

ova/gui/soundscape.py with play_ambient(theme), play_sting(), duck_for_tts(), stop().

### 5. Mail / pet loop
1. Steward or Komodo drafts a paint STEP (theme + prompt).
2. Claw/steward runs Diffusers or Comfy when VRAM free; returns PROOF tree+sha256.
3. WHI: Ax-PAINT / Ax-GUI facts; copy into data/artifacts/gui/ only after HIL like.
4. Optional hearthbeat verb later: gui.theme_set args {theme: lunar}.

### 6. Fix-forward for Comfy on TUF
- Restore or keep comfy\sd.py stub; better: allowlist the blocked SciPy Highs DLL in Windows Application Control, or pin a SciPy build without _highs_options.
- Until then, **Diffusers backend** is the reliable NOVA paint path on this metal.

---

## PROOF (this drop)
Images: 4 PNGs in STAGING/gui_art/
Music: 5 WAVs in STAGING/gui_music/
See GUI_ASSETS_MANIFEST_2026-09-26.json for sha256 of each file.
GPU after mint: idle again (~147 MiB used when checked).
