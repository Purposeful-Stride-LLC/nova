"""NOVA ear STT — push-to-talk / cue-gated, faster-whisper on CPU.

Like cam:0: capture → artifact → Tx-EAR fact. No always-on mic. No GPU claim.
Pocket TTS remains OUT only.
"""
from __future__ import annotations

import json
import time
import wave
from pathlib import Path
from typing import Any

from nova import db, office

DEFAULT_MODEL = "base.en"
DEFAULT_SECONDS = 4.0
SAMPLE_RATE = 16000


def _art_dir() -> Path:
    d = db.home() / "data" / "artifacts" / "hearing"
    d.mkdir(parents=True, exist_ok=True)
    return d


def record_wav(seconds: float = DEFAULT_SECONDS, path: Path | None = None) -> dict[str, Any]:
    """HIL capture: record mic for N seconds to wav. Requires sounddevice."""
    try:
        import sounddevice as sd
        import numpy as np
    except Exception as exc:
        return {"ok": False, "error": f"mic deps: {exc}"}
    seconds = max(0.5, min(float(seconds), 30.0))
    dest = path or (_art_dir() / f"ear_{db.zulu().replace(':', '')}.wav")
    try:
        frames = int(seconds * SAMPLE_RATE)
        audio = sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype="int16")
        sd.wait()
    except Exception as exc:
        return {"ok": False, "error": f"record: {exc}"}
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(audio.tobytes())
    return {"ok": True, "path": str(dest.resolve()), "seconds": seconds, "rate": SAMPLE_RATE}


def transcribe(path: str, model: str = DEFAULT_MODEL, device: str = "cpu") -> dict[str, Any]:
    """faster-whisper on CPU by default (share NVIDIA with other pets)."""
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        return {"ok": False, "error": f"faster_whisper: {exc}"}
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": "no wav"}
    try:
        wm = WhisperModel(model, device=device, compute_type="int8")
        segs, info = wm.transcribe(str(p), beam_size=1, vad_filter=True)
        text = " ".join((s.text or "").strip() for s in segs).strip()
        return {
            "ok": True,
            "text": text[:4000],
            "lang": getattr(info, "language", None),
            "model": model,
            "device": device,
            "path": str(p.resolve()),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": str(p)}


def listen(
    seconds: float = DEFAULT_SECONDS,
    model: str = DEFAULT_MODEL,
    approve: bool = False,
    device: str = "cpu",
) -> dict[str, Any]:
    """PTT HIL: approve=True required to open mic. Writes wav + Tx-EAR."""
    if not approve:
        return {
            "ok": False,
            "error": "HIL: pass approve=True to open mic (push-to-talk)",
            "hint": "ear_stt.listen(approve=True, seconds=4)",
        }
    rec = record_wav(seconds=seconds)
    if not rec.get("ok"):
        return rec
    tx = transcribe(rec["path"], model=model, device=device)
    packet = {
        "whi": "Tx-EAR",
        "zulu": db.zulu(),
        "path": rec.get("path"),
        "seconds": rec.get("seconds"),
        "model": model,
        "device": device,
        "text": (tx.get("text") or "")[:4000],
        "tx_ok": bool(tx.get("ok")),
        "tx_err": tx.get("error"),
        "lang": tx.get("lang"),
    }
    name = f"Tx-EAR_stt_{db.zulu().replace(':', '')}.json"
    dest = _art_dir() / name
    dest.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    db.put_fact("Tx-EAR", Path(rec["path"]).name, json.dumps(packet, ensure_ascii=False)[:4000])
    try:
        office.post_packet(
            dest="ear@local",
            mask="sentinel",
            whi="Tx-EAR",
            kind="stt",
            cite=rec.get("path") or "ear_stt",
            body=json.dumps(packet, ensure_ascii=False)[:3000],
        )
    except Exception:
        pass
    return {"ok": bool(tx.get("ok")), **packet, "artifact": str(dest)}


def smoke_offline(model: str = "tiny.en") -> dict[str, Any]:
    """No mic: synthesize silence wav + load model (GPU-safe CPU)."""
    dest = _art_dir() / f"ear_smoke_{int(time.time())}.wav"
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(b"\\x00\\x00" * SAMPLE_RATE)  # 1s silence
    tx = transcribe(str(dest), model=model, device="cpu")
    return {"ok": bool(tx.get("ok")), "path": str(dest), "tx": tx}


def listen_file(path: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """Transcribe existing wav (no mic). Stamps Tx-EAR."""
    tx = transcribe(path, model=model, device="cpu")
    if not tx.get("ok"):
        return tx
    packet = {
        "whi": "Tx-EAR",
        "zulu": db.zulu(),
        "path": str(Path(path).resolve()),
        "model": model,
        "device": "cpu",
        "text": tx.get("text") or "",
        "lang": tx.get("lang"),
        "mode": "file",
    }
    db.put_fact("Tx-EAR", Path(path).name, json.dumps(packet, ensure_ascii=False)[:4000])
    return {"ok": True, **packet}
