"""Vision + hearing parsers. OpenCV / wave first. VLM optional. GIS later."""

from __future__ import annotations

import json
import struct
import wave
from pathlib import Path

from nova import db, office

VISION_HINTS = ("moondream", "llava", "minicpm", "qwen2-vl", "qwen2.5vl", "qwen3-vl", "llama3.2-vision", "bakllava")


def vision_tags(names: list[str] | None = None) -> list[str]:
    if names is None:
        from nova import ollama_talk

        names = ollama_talk.tags()
    return [n for n in names if any(h in n.lower() for h in VISION_HINTS)]


def _features(img) -> dict:
    import cv2
    import numpy as np

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    mean = float(gray.mean())
    edges = cv2.Canny(gray, 80, 160)
    edge_pct = float(edges.mean() / 255.0)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = sorted((cv2.contourArea(c) for c in cnts), reverse=True)[:8]
    return {
        "w": int(w),
        "h": int(h),
        "mean_luma": round(mean, 1),
        "edge_pct": round(edge_pct, 4),
        "n_contours": len(cnts),
        "top_areas": [round(a, 1) for a in areas],
    }


def pair_motion(a, b) -> dict:
    import cv2

    ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    ga = cv2.GaussianBlur(ga, (21, 21), 0)
    gb = cv2.GaussianBlur(gb, (21, 21), 0)
    delta = cv2.absdiff(ga, gb)
    _, th = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)
    th = cv2.dilate(th, None, iterations=2)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    big = [c for c in cnts if cv2.contourArea(c) > 400]
    return {"motion_blobs": len(big), "delta_mean": round(float(delta.mean()), 2)}


def save_still(index: int = 0, owner: str = "steward") -> dict:
    from nova.hands import cameras

    raw = cameras.snapshot(index)
    if not raw.get("ok"):
        return raw
    src = Path(raw["path"])
    z = db.zulu().replace(":", "")
    name = f"Ax-CAM-{index}_{owner}_{z}.jpg"
    dest = db.home() / "data" / "artifacts" / "vision"
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / name
    try:
        import cv2

        img = cv2.imread(str(src))
        if img is None:
            return {"ok": False, "error": "unreadable frame"}
        cv2.imwrite(str(out), img)
        feat = _features(img)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    packet = {
        "whi": f"Tx-CAM-{index}",
        "path": str(out),
        "owner": owner,
        "zulu": db.zulu(),
        "features": feat,
        "cite": f"opencv:{index}",
    }
    db.put_fact("Tx-CAM", name, json.dumps(packet))
    office.post_packet(dest="seer@local", mask="chronicler", whi=packet["whi"], kind="vision", cite=str(out), body=json.dumps(feat))
    return {"ok": True, **packet}


def describe(path: str, model: str | None = None) -> dict:
    """Optional VLM. Roster must contain a vision tag."""
    tags = vision_tags()
    model = model or (tags[0] if tags else "")
    if not model:
        return {"ok": False, "error": "no vision tag. ollama pull moondream"}
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": "no image"}
    import base64
    import json as js
    import urllib.request

    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    body = js.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Describe scene. Objects. Motion guess. No flourish.",
                    "images": [b64],
                }
            ],
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = js.loads(r.read().decode())
        text = (data.get("message") or {}).get("content") or ""
    except Exception as exc:
        return {"ok": False, "error": str(exc), "model": model}
    db.put_fact("Tx-CAM", f"vlm-{p.name}", text[:2000])
    office.bump("seer@local", "jobs_run")
    return {"ok": True, "model": model, "text": text[:800]}


def wav_features(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": "no wav"}
    with wave.open(str(p), "rb") as w:
        nch, sw, rate, nframes, _, _ = w.getparams()
        raw = w.readframes(min(nframes, rate * 8))
    if sw != 2:
        return {"ok": False, "error": f"need 16-bit wav got sw={sw}"}
    n = len(raw) // 2
    samples = struct.unpack("<" + "h" * n, raw)
    if not samples:
        return {"ok": False, "error": "empty"}
    mean = sum(samples) / n
    rms = (sum((s - mean) ** 2 for s in samples) / n) ** 0.5
    zc = sum(1 for i in range(1, n) if samples[i - 1] * samples[i] < 0) / max(n, 1)
    packet = {
        "whi": "Tx-EAR",
        "path": str(p.resolve()),
        "rate": rate,
        "nch": nch,
        "rms": round(rms, 1),
        "zcr": round(zc, 4),
        "seconds": round(n / float(rate * max(nch, 1)), 2),
        "zulu": db.zulu(),
    }
    name = f"Tx-EAR_steward_{db.zulu().replace(':','')}.json"
    dest = db.home() / "data" / "artifacts" / "hearing"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / name).write_text(json.dumps(packet), encoding="utf-8")
    db.put_fact("Tx-EAR", p.name, json.dumps(packet))
    office.post_packet(dest="ear@local", mask="sentinel", whi="Tx-EAR", kind="audio", cite=str(p), body=json.dumps(packet))
    return {"ok": True, **packet}


def fuse(cam_fact: dict, ear_fact: dict) -> dict:
    """Same-window cross-check. Council packet. No GIS."""
    body = {"vision": cam_fact, "hearing": ear_fact, "note": "zulu-near pair. HIL before act."}
    office.post_packet(
        dest="brief@local",
        mask="brief",
        whi="Tx-FUSE",
        kind="council",
        cite="senses.fuse",
        body=json.dumps(body)[:3000],
    )
    office.report(2, "fuse vision+ear", json.dumps(body)[:500])
    return body
