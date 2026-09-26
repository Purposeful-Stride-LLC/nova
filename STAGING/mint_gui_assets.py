#!/usr/bin/env python3
"""Mint NOVA GUI backgrounds via ComfyUI API + procedural ambient beds."""
from __future__ import annotations

import json
import math
import os
import random
import shutil
import struct
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
CKPT = os.environ.get("COMFY_CKPT", "v1-5-pruned-emaonly.safetensors")
FK = Path(os.environ.get("NOVA_FIELDKIT", str(Path.home() / "Documents" / "NOVA" / "NOVA_fieldkit_v1_4")))
OUT_IMG = FK / "STAGING" / "gui_art"
OUT_MUSIC = FK / "STAGING" / "gui_music"
COMFY_OUT = Path(os.environ.get("COMFY_OUTPUT", str(Path.home() / "Projects" / "ComfyUI" / "output")))
DATE = "2026-09-26"

PROMPTS = [
    (
        "nova_gui_bg_dark_homestead",
        "cinematic dark rural homestead night, soft warm window lamps, deep navy and black sky, empty wide composition for UI chrome overlay, subtle fog, no people, no text, no logos, soft bokeh, matte painting, 8k",
    ),
    (
        "nova_gui_bg_lunar_command",
        "lunar command deck interior, cool blue glass panels, curved moon horizon through viewport, sparse holographic UI glow, empty composition for overlays, no people, no text, no logos, cinematic, clean sci-fi",
    ),
    (
        "nova_gui_bg_frostshield_glass",
        "frostshield translucent icy glass panes, soft cyan rim light, crystalline HUD emptiness, cold atmosphere, abstract architectural glass, no people, no text, no logos, elegant minimal",
    ),
    (
        "nova_gui_bg_warm_forge",
        "warm forge ember glow charcoal and amber, soft volumetric light, empty workshop backdrop for UI, shallow depth of field, no people, no text, no logos, cozy industrial sci-fi",
    ),
]

NEG = "text, watermark, logo, UI widgets, buttons, busy clutter, faces, people, deformed, lowres, jpeg artifacts"


def http_json(method: str, path: str, data=None, timeout=120):
    url = COMFY.rstrip("/") + path
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def wait_comfy(max_s=180):
    t0 = time.time()
    while time.time() - t0 < max_s:
        try:
            http_json("GET", "/system_stats", timeout=3)
            return True
        except Exception:
            time.sleep(2)
    return False


def workflow(prompt: str, seed: int):
    # Standard SD1.5 txt2img graph for Comfy API
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CKPT},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 768, "height": 512, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEG, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": f"nova_gui_{DATE}", "images": ["8", 0]},
        },
    }


def queue_prompt(prompt: str, seed: int) -> str:
    payload = {"prompt": workflow(prompt, seed), "client_id": "nova-steward"}
    res = http_json("POST", "/prompt", payload)
    return res["prompt_id"]


def wait_history(prompt_id: str, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            hist = http_json("GET", f"/history/{prompt_id}", timeout=30)
            if hist and prompt_id in hist:
                return hist[prompt_id]
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(prompt_id)


def newest_png_after(t0: float) -> Path | None:
    cands = []
    for p in COMFY_OUT.rglob("*.png"):
        try:
            if p.stat().st_mtime >= t0 - 1:
                cands.append(p)
        except OSError:
            pass
    if not cands:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def mint_images():
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    if not wait_comfy():
        raise SystemExit("ComfyUI not ready on 8188")
    results = []
    for i, (name, prompt) in enumerate(PROMPTS):
        seed = 26092600 + i * 17
        print(f"[img] queue {name} seed={seed}")
        t0 = time.time()
        pid = queue_prompt(prompt, seed)
        hist = wait_history(pid)
        # Prefer history outputs
        src = None
        outs = (hist.get("outputs") or {}).get("9", {}).get("images") or []
        if outs:
            meta = outs[0]
            sub = meta.get("subfolder") or ""
            src = COMFY_OUT / sub / meta["filename"] if sub else COMFY_OUT / meta["filename"]
        if not src or not src.exists():
            src = newest_png_after(t0)
        if not src or not src.exists():
            raise FileNotFoundError(f"no png for {name}")
        dest = OUT_IMG / f"{name}_{DATE}.png"
        shutil.copy2(src, dest)
        results.append({"name": name, "path": str(dest), "bytes": dest.stat().st_size, "seed": seed, "prompt": prompt, "src": str(src)})
        print(f"[img] saved {dest}")
    return results


def write_wav(path: Path, samples, rate=44100):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples)
        w.writeframes(frames)


def tone_bed(seconds: float, root_hz: float, overtones, rate=44100, breath=0.15):
    n = int(seconds * rate)
    out = []
    for i in range(n):
        t = i / rate
        env = min(1.0, t / 2.0) * min(1.0, (seconds - t) / 3.0)
        # soft pulse
        pulse = 0.55 + 0.45 * math.sin(2 * math.pi * (0.08 + breath * 0.02) * t)
        s = 0.0
        for mul, amp in overtones:
            s += amp * math.sin(2 * math.pi * root_hz * mul * t + 0.3 * math.sin(0.05 * t))
        # gentle noise dust
        s += 0.02 * (random.random() * 2 - 1)
        out.append(s * env * pulse * 0.22)
    return out


def mint_music():
    OUT_MUSIC.mkdir(parents=True, exist_ok=True)
    specs = [
        ("nova_gui_ambient_homestead", 48.0, 110.0, [(1, 0.55), (2, 0.18), (3, 0.08), (0.5, 0.25)]),
        ("nova_gui_ambient_lunar", 56.0, 98.0, [(1, 0.5), (1.5, 0.2), (2, 0.12), (4, 0.05)]),
        ("nova_gui_ambient_frostshield", 52.0, 130.0, [(1, 0.45), (2, 0.22), (5, 0.06), (0.5, 0.2)]),
        ("nova_gui_ambient_forge", 44.0, 82.0, [(1, 0.6), (2, 0.15), (3, 0.1), (0.5, 0.18)]),
    ]
    results = []
    for name, secs, root, over in specs:
        path = OUT_MUSIC / f"{name}_{DATE}.wav"
        print(f"[music] synthesize {name}")
        write_wav(path, tone_bed(secs, root, over))
        results.append({"name": name, "path": str(path), "bytes": path.stat().st_size, "seconds": secs, "root_hz": root})
    # short loop sting for tile focus
    sting = OUT_MUSIC / f"nova_gui_sting_focus_{DATE}.wav"
    write_wav(sting, tone_bed(2.5, 220.0, [(1, 0.7), (2, 0.25), (3, 0.1)], breath=0.4))
    results.append({"name": "nova_gui_sting_focus", "path": str(sting), "bytes": sting.stat().st_size, "seconds": 2.5, "root_hz": 220.0})
    return results


def main():
    imgs = mint_images()
    music = mint_music()
    manifest = {"zulu": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "images": imgs, "music": music}
    man = OUT_IMG.parent / f"GUI_ASSETS_MANIFEST_{DATE}.json"
    man.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("MANIFEST", man)
    print(json.dumps({"images": len(imgs), "music": len(music)}, indent=2))


if __name__ == "__main__":
    main()
