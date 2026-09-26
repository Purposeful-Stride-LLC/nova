# Prerequisites checklist — ComfyUI paint method

## Software
- [x] Git
- [x] Python 3.12 (separate from NOVA fieldkit 3.14)
- [x] ComfyUI git clone
- [x] venv + requirements.txt
- [x] PyTorch **CUDA cu128** (sm_120 / RTX 5050)
- [x] ComfyUI-GGUF custom node (for future Qwen GGUF)
- [ ] Optional: Hugging Face login for gated models
- [ ] Optional: Qwen-Image GGUF weights (phase 2)

## Hardware
- [x] NVIDIA GPU with drivers
- [x] ≥8 GB VRAM (TUF: 8 GB shared — one heavy workload at a time)
- [x] Disk: prefer ≥40 GB free on C: for Comfy+starter+optional Qwen

## Operational
- [x] Cold-start script (stop competing GPU users)
- [x] Port 8188 free (not hearthbeat)
- [x] Avatar pipeline left alone