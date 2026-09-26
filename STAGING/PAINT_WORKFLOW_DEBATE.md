# Paint workflow debate — Qwen-Image-2.1
2026-09-21 02:25 local

## What dropped
Qwen-Image-2.1 (2026-09-20): unified text-to-image + edit, ~7B DiT + Qwen3-VL encoder, native RGBA, up to 10 refs, Diffusers \QwenImage21Pipeline\ + ComfyUI day-zero.
NOT an Ollama model. Ollama runs LLMs/VLMs (moondream sees; does not paint).

## License (product-critical)
Qwen Research License = non-commercial research/eval by default. Commercial wrap into Purposeful Stride / NOVA Command needs a separate Alibaba license conversation — do not silently ship product paint on these weights.

## Metal facts (TUF probe)
- torch: yes | diffusers: no | PIL: no | cv2: yes
- GPU: RTX 5050 Laptop 8151 MiB; at probe ~6390 used / 1521 free
- vision: moondream see works (cam still described)
- nova brief: "Defer. Risk: GPU contention. Next cut: Evaluate resource allocation before integration."

## Debate options
A) **Separate paint pet** (recommended staging): ova/paint.py\ + leash — Diffusers or ComfyUI API, HIL approve, GPU mutex (refuse if Claw/chamber hot), write Ax-PAINT artifact + Tx-PAINT fact. Mirror speak/ear gates.
B) Jam into Ollama seats: **reject** — wrong runtime; will thrash shared 8GB card.
C) Steward-cloud paint (Grok Bot GenerateImage): fine for staging mocks / glass demos; not sovereign metal; different look/feel than Qwen-Image.
D) Quantized local later: only after GPU budget + Diffusers install + license path; target when free VRAM >=~6-8GB alone (may still be tight on 8GB laptop for full 2.1).

## Proposed workflow (staging -> integration)
1. Staging: steward sim images + methodology docs (this file); no weight download yet
2. Chamber motion when GPU free: paint pet shape, WHI codes, PROOF (bytes=N on png)
3. Integration smoke: install diffusers+PIL; dry-run pipeline load; one HIL paint; compare to steward sim
4. Product: only after license clarity + GPU mutex + GC for old paints in artifacts

## Do not
- ollama pull anything named qwen-image hoping it paints
- Run paint concurrent with Aurelius/chamber
- Treat research weights as product-ready
