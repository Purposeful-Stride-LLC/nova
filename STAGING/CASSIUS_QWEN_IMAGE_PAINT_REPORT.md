# Cassius — Qwen-Image paint research + lean NOVA wire (2026-09-22)

Assignment: Qwen-image research + lean paint path for NOVA. Avatar stays Claw/Aurelius lane.

## Metal facts (TUF, re-probed)

| Item | Value |
|------|--------|
| GPU | NVIDIA GeForce RTX 5050 Laptop, **8151 MiB** |
| At probe | ~6390 used / ~1520 free (shared with Ollama seats) |
| Ollama | LLM/VLM only: qwen3/qwen3.5, moondream (see), etc. **No paint** |
| Python 3.14 | `torch 2.14.0+cpu`, **cuda False**; no `diffusers` / PIL in this interpreter |
| Avatar assets | `D:\pg\ai\nova-ai\agents\avatar\` (~80 mp4 mood clips + player) — **do not replace with diffusion** |
| Prior steward docs | `PAINT_WORKFLOW_DEBATE.md`, `PAINT_BOX_VS_METAL.md`, `PAINT_METAL_PROBE.json`, `AVATAR_*` |

## What “Qwen-Image” actually is

- **Qwen-Image / Qwen-Image-Edit** = diffusion (MMDiT) text-to-image / edit — **Diffusers or ComfyUI**, not Ollama.
- **Qwen2-VL / moondream** = vision-language **see**, not paint. Already on metal via moondream.
- Confusing names with `qwen3:8b` / Komodo coder — those are chat/code, not image gen.

### VRAM realism on 8GB

| Path | Approx VRAM | Fit on TUF 8GB? |
|------|-------------|-----------------|
| Qwen-Image FP16 | ~40–60+ GB | **No** |
| FP8 | ~22–24 GB | **No** |
| 4-bit / heavy offload | ~14–18 GB class | **No** (needs headroom; card already hot) |
| GGUF Q2_K + ComfyUI + encoder in RAM | ~7+ GB unet alone, fragile | **Park / experimental only** when GPU cold + no Claw |
| Full live default | — | **Park** |

**Recommendation: PARK live Qwen-Image weights on TUF.** Keep a lean **paint pet stub** that refuses safely, with a future ComfyUI/Diffusers backend behind HIL + thermal mutex. Prefer steward/box `GenerateImage` for demos; sovereign metal paint only after GPU budget + license path.

### License (product)

Qwen Image research licenses are often **non-commercial by default**. Purposeful Stride / product wrap needs an explicit Alibaba/commercial conversation — do not silently ship as product paint.

## Where it must NOT fight the avatar pipeline

Per `AVATAR_TOOLBOX_DOCTRINE` / `AVATAR_PANEL_PIPELINE`:

- Face = **pre-shot mp4 panels** + Pocket TTS (+ optional rare moondream on 1–3 frames).
- **Do not** diffusion-generate Nova’s face.
- Paint pet writes under `data/artifacts/paint/` only — never into `agents/avatar/`.
- No concurrent paint with Aurelius/chamber when GPU warm (use `nova.thermal.gate`).

## Lean hook design

```
nova/hands/paint.py     # L0 pet: status / refuse / optional future backend
  paint.status()
  paint.generate(prompt, hil=True)  # default PARKED → structured refuse
  artifacts → data/artifacts/paint/*.png + Ax-PAINT / Tx-PAINT
  thermal.gate("paint") or stricter free-VRAM check inside paint
TUI (later, Varro): /paint PROMPT  — only after unpark
Leash: optional paint STEP — never auto-unpark
```

Backend options when unparked later (not implemented now):

1. **ComfyUI HTTP** on localhost (GGUF Qwen-Image) — best isolation; start only when cold.
2. **Diffusers** in a CUDA-enabled venv (not the CPU torch 3.14 seat).
3. **Steward relay** — call box GenerateImage for glass mocks (already proven in PAINT_BOX_VS_METAL).

## Deliverables written

| Path | Role |
|------|------|
| `STAGING/CASSIUS_QWEN_IMAGE_PAINT_REPORT.md` | This note |
| `nova/hands/paint.py` | Parked paint hand (safe refuse + status + artifact dir) |
| `STAGING/CASSIUS_PAINT_PATCH_LIST.md` | Optional TUI/sched wire steps for steward |

## Blockers

1. **8GB shared GPU** — full Qwen-Image not realistic alongside Ollama.
2. **Default Python torch is CPU-only** — need separate CUDA venv or ComfyUI for any local paint.
3. **License** for commercial product use unclear.
4. **No weight download** performed (by design — park).

## Ask for Varro / Michael

- Confirm **PARK** as standing policy until a dedicated GPU window or ComfyUI sidecar.
- If unpark desired: prefer **ComfyUI sidecar** over stuffing Diffusers into fieldkit Python.
- Greenlight TUI `/paint` wire only after one cold-GPU smoke.