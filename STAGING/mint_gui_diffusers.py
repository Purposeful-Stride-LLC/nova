#!/usr/bin/env python3
"""Fallback: mint GUI PNGs with diffusers + local SD1.5 checkpoint (no Comfy server)."""
from __future__ import annotations
import json, time
from pathlib import Path

CKPT = Path.home() / "Projects" / "ComfyUI" / "models" / "checkpoints" / "v1-5-pruned-emaonly.safetensors"
OUT = Path.home() / "Documents" / "NOVA" / "NOVA_fieldkit_v1_4" / "STAGING" / "gui_art"
DATE = "2026-09-26"
NEG = "text, watermark, logo, UI widgets, buttons, busy clutter, faces, people, deformed, lowres, jpeg artifacts"
PROMPTS = [
    ("nova_gui_bg_dark_homestead", "cinematic dark rural homestead night, soft warm window lamps, deep navy and black sky, empty wide composition for UI chrome overlay, subtle fog, no people, no text, no logos, soft bokeh, matte painting"),
    ("nova_gui_bg_lunar_command", "lunar command deck interior, cool blue glass panels, curved moon horizon through viewport, sparse holographic UI glow, empty composition for overlays, no people, no text, no logos, cinematic, clean sci-fi"),
    ("nova_gui_bg_frostshield_glass", "frostshield translucent icy glass panes, soft cyan rim light, crystalline HUD emptiness, cold atmosphere, abstract architectural glass, no people, no text, no logos, elegant minimal"),
    ("nova_gui_bg_warm_forge", "warm forge ember glow charcoal and amber, soft volumetric light, empty workshop backdrop for UI, shallow depth of field, no people, no text, no logos, cozy industrial sci-fi"),
]

def main():
    import torch
    from diffusers import StableDiffusionPipeline
    OUT.mkdir(parents=True, exist_ok=True)
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("device", device, "dtype", dtype, "ckpt", CKPT)
    pipe = StableDiffusionPipeline.from_single_file(str(CKPT), torch_dtype=dtype, safety_checker=None, requires_safety_checker=False)
    pipe = pipe.to(device)
    pipe.set_progress_bar_config(disable=False)
    results = []
    for i, (name, prompt) in enumerate(PROMPTS):
        seed = 26092600 + i * 17
        g = torch.Generator(device=device).manual_seed(seed)
        print("gen", name, seed)
        img = pipe(prompt=prompt, negative_prompt=NEG, width=768, height=512, num_inference_steps=20, guidance_scale=7.0, generator=g).images[0]
        dest = OUT / f"{name}_{DATE}.png"
        img.save(dest)
        results.append({"name": name, "path": str(dest), "bytes": dest.stat().st_size, "seed": seed, "prompt": prompt})
        print("saved", dest)
    man = OUT.parent / f"GUI_ASSETS_MANIFEST_IMAGES_{DATE}.json"
    man.write_text(json.dumps({"zulu": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "backend": "diffusers", "images": results}, indent=2), encoding="utf-8")
    print("MANIFEST", man)

if __name__ == "__main__":
    main()
