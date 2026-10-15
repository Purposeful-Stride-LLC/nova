"""Mail TCP framing constants + helpers (Fieldkit 2.0).

Can import from hearthbeat or stand alone lightly.
"""
from __future__ import annotations

import json
import socket
import struct

# Prefer hearthbeat as source of truth when available.
try:
    from nova.hearthbeat import BEACON_PORT, DEFAULT_HOST, JOB_PORT, MAX_FRAME
except Exception:  # pragma: no cover
    DEFAULT_HOST = "192.0.2.10"
    BEACON_PORT = 41776
    JOB_PORT = 41777
    MAX_FRAME = 8_000_000

BEACON_PORT = 41776
JOB_PORT = 41777
MAX_FRAME = 8_000_000


def recv_frame(conn: socket.socket) -> dict:
    hdr = b""
    while len(hdr) < 4:
        chunk = conn.recv(4 - len(hdr))
        if not chunk:
            raise ConnectionError("closed")
        hdr += chunk
    (n,) = struct.unpack("!I", hdr)
    if n > MAX_FRAME:
        raise ValueError(f"frame_too_large:{n}")
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(min(65536, n - len(buf)))
        if not chunk:
            raise ConnectionError("closed_mid_frame")
        buf += chunk
    return json.loads(buf.decode("utf-8"))


def send_frame(conn: socket.socket, obj: dict) -> None:
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    conn.sendall(struct.pack("!I", len(raw)) + raw)


__all__ = [
    "BEACON_PORT",
    "DEFAULT_HOST",
    "JOB_PORT",
    "MAX_FRAME",
    "recv_frame",
    "send_frame",
]
