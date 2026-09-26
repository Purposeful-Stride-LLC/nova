"""TUF hub client for Hearthbeat tentacle mail over TCP 41776/41777."""
from __future__ import annotations
import json, socket, struct, time, uuid
from pathlib import Path

DEFAULT_HOST = "192.168.0.76"
BEACON_PORT = 41776
JOB_PORT = 41777
MAX_FRAME = 8_000_000

def _recv_frame(conn: socket.socket) -> dict:
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

def _send_frame(conn: socket.socket, obj: dict) -> None:
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    conn.sendall(struct.pack("!I", len(raw)) + raw)

def ping(host: str = DEFAULT_HOST, port: int = BEACON_PORT, timeout: float = 8.0, from_id: str = "tuf-hub") -> dict:
    msg = {"v": 1, "kind": "ping", "from": from_id, "to": "og-ubuntu", "zulu": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with socket.create_connection((host, port), timeout=timeout) as conn:
        conn.settimeout(timeout)
        _send_frame(conn, msg)
        return _recv_frame(conn)

def submit(job: dict, host: str = DEFAULT_HOST, port: int = JOB_PORT, timeout: float = 120.0) -> dict:
    job = dict(job)
    job.setdefault("job_id", f"hub-{uuid.uuid4().hex[:10]}")
    with socket.create_connection((host, port), timeout=timeout) as conn:
        conn.settimeout(timeout)
        _send_frame(conn, job)
        return _recv_frame(conn)

def smoke(host: str = DEFAULT_HOST) -> dict:
    pong = ping(host)
    health = submit({"kind": "health"}, host=host, timeout=30)
    return {"pong": pong, "health": health}
