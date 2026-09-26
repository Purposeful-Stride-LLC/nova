# NOVA paint sidecar â€” ComfyUI on TUF

Installed by Cassius 2026-09-22 for Michael. Outside fieldkit core.

## Where

| Item | Path |
|------|------|
| ComfyUI root | `Projects\ComfyUI` |
| Python venv | `Projects\ComfyUI\.venv` (Python 3.12 + torch **2.11+cu128**) |
| Checkpoints | `models\checkpoints\` |
| GGUF unets (Qwen later) | `models\unet\` |
| Text encoders | `models\text_encoders\` |
| VAE | `models\vae\` |
| Custom node GGUF | `custom_nodes\ComfyUI-GGUF` |
| Outputs | `ComfyUI\output\` |
| NOVA paint artifacts (optional copy) | fieldkit `data\artifacts\paint\` |

## Prerequisites (met on TUF)

| Need | Status |
|------|--------|
| Disk (C:) | ~125 GB free before install; ComfyUI+torch ~8â€“12 GB; SD1.5 ~4 GB; Qwen GGUF stack ~15â€“35 GB optional |
| GPU | RTX 5050 Laptop 8 GB â€” **shared** with Ollama |
| CUDA torch | **cu128** required for sm_120 (Blackwell). cu124 does **not** run matmul on this card |
| Python | 3.12.10 (winget `Python.Python.3.12`) â€” not fieldkitâ€™s 3.14 CPU torch |
| Git | present |
| Ports | ComfyUI default **8188** â€” do not collide with hearthbeat 41776/41777 |

## Method / workflow (cold GPU)

ComfyUI is a **code resource + UI scheduler** for image graphs (nodes, samplers, models).  
It is the paint pet Varro/Cassius agreed on â€” **not** jammed into Ollama seats.

1. **Stop / idle Ollama** (and any Claw/chamber GPU jobs) so VRAM frees up.
2. Run `NOVA_PAINT\cold_start.bat` â†’ opens http://127.0.0.1:8188
3. Load a workflow (starter: Load Checkpoint â†’ CLIP Text Encode â†’ KSampler â†’ VAE Decode â†’ Save Image).
4. Generate; images land in `output\`.
5. Run `NOVA_PAINT\cold_stop.bat` when done; restart Ollama if needed.

Default NOVA `hands/paint.py` stays **PARKED** until you set `NOVA_PAINT=1` and point `NOVA_PAINT_BACKEND=comfyui` after a successful smoke.

## Models

### Phase 1 â€” works now on 8GB
- **Stable Diffusion 1.5** `v1-5-pruned-emaonly.safetensors` in `models\checkpoints\`  
  Reliable, small, good for learning the scheduler/node graph.

### Phase 2 â€” Qwen-Image (optional, heavier)
Qwen-Image is **not** an Ollama model. Use ComfyUI + GGUF node:

| Piece | Approx size | Notes |
|-------|-------------|--------|
| Qwen-Image unet GGUF Q2_K | ~7 GB | Only quant class that might scrape into 8GB; quality soft |
| Q4_K_M | ~12â€“13 GB | Usually needs more VRAM / offload |
| Text encoder (Qwen2.5-VL) | several GB | Often RAM-offloaded |
| VAE | ~300 MB | |

**License:** Qwen Image research weights may be non-commercial by default â€” confirm before product wrap.

Download command (when ready; needs free disk + cold GPU):

```bat
cd Projects\ComfyUI
.venv\Scripts\huggingface-cli download QuantStack/Qwen-Image-GGUF --local-dir models\unet\qwen-image-gguf
```

(Exact repo names change â€” verify on Hugging Face before large pulls.)

## Avatar lane

**Do not** write face clips here. Nova face = `D:\pg\ai\nova-ai\agents\avatar\` + Pocket TTS (Claw/Aurelius).

## Quick smoke

```bat
cd Projects\ComfyUI
NOVA_PAINT\cold_start.bat
```

Browser â†’ Load default graph â†’ pick `v1-5-pruned-emaonly.safetensors` â†’ Queue Prompt.

## Qwen-Image-2.0 (cloud) vs Qwen-Image-2.1 (local 7B)

Michael pointed at https://www.qwencloud.com/models/qwen-image-2.0 — that page is the **QwenCloud / DashScope API** (`model="qwen-image-2.0"`, ~$0.035/image, DashScope key). It is **not** an Ollama pull and not the same as dumping weights into ComfyUI.

| Path | What | Fits TUF 8GB? |
|------|------|----------------|
| **Cloud API** `qwen-image-2.0` | Paid HTTP paint | Yes (no local VRAM) |
| **Local open weights** `Qwen/Qwen-Image-2.1` / `Comfy-Org/Qwen-Image-2.1` | **7B DiT** + separate text encoder (~8–9B class) + VAE | Tight — INT8 stack peaks ~14GB in reports; needs cold GPU + offload/quant; may OOM |
| Old “Qwen-Image” 20B line | Heavier | No |

### Local ComfyUI files (lean pack)

Place under ComfyUI (download in progress / done):

```
models/diffusion_models/qwen_image_2.1_int8_convrot.safetensors   (~7.3 GB)
models/text_encoders/qwen3vl_8b_w4a8.safetensors                  (~6.3 GB)
models/vae/qwen_image_2.1_vae_bf16.safetensors                    (~0.7 GB)
```

Use ComfyUI’s built-in **Qwen Image 2.1** templates (needs recent ComfyUI). Cold-start only.

### Cloud API (matches the link)

Needs `DASHSCOPE_API_KEY` (or QwenCloud key). Example uses `dashscope` + `model="qwen-image-2.0"`. Good for product demos without fighting Ollama VRAM. Keep secrets out of palace.

Research license on open weights may still be non-commercial for product wrap — confirm before shipping.