# Ax — ComfyUI paint sidecar (steward pointer)

Zulu: 2026-09-22T12:12:52Z
Source: Cassius completion

- Tree: `Projects\ComfyUI`
- Cold start/stop: `NOVA_PAINT\cold_start.bat` / `cold_stop.bat`
- Docs: folder README + PREREQS; `STAGING/CASSIUS_COMFYUI_SETUP.md`
- Torch 2.11+cu128; starter SD1.5 checkpoint; ComfyUI-GGUF for future Qwen
- Port **8188** only (not hearthbeat 41776/41777)
- Policy: **PARK** default while Ollama/council share RTX; unpark only for cold-GPU window
- Paint hand aware of comfyui_root; avatar lane untouched
