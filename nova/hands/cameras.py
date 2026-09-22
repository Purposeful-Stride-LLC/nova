from __future__ import annotations

import sys

from nova import db


def snapshot(index: int = 0) -> dict:
    try:
        import cv2
    except ImportError:
        return {"ok": False, "error": "pip install opencv-python-headless"}
    cap = cv2.VideoCapture(int(index), cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(int(index))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return {"ok": False, "error": f"no frame on {index}"}
    dest = db.home() / "data" / "artifacts"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"cam_{index}.jpg"
    cv2.imwrite(str(path), frame)
    db.put_fact("Tx-CAM", f"cam-{index}", str(path))
    return {"ok": True, "path": str(path), "index": int(index)}
