"""Bluetooth RFCOMM fallback link for the NOVA tentacle (Fieldkit 2.0).

Standalone, standard library only. NOT wired into the daemon; existing mail
code (protocol.py / hearthbeat TCP 41776/41777) is untouched.

Framing: JSON lines. One compact UTF-8 JSON object per line, ending in "\n".
Envelope fields match nova.hearthbeat: v, kind, from, to, zulu, plus
id, ts (epoch seconds) and body. The server answers every packet with
kind="ack" (re=<id>). Kinds: beacon, ping, ack, or any other string.

  python -m nova.mail.bt_link serve [--channel 3] [--once]
  python -m nova.mail.bt_link send --addr XX:XX:XX:XX:XX:XX [--channel 3] [--kind beacon] [--body TEXT]

Every received packet is appended to STAGING\\bt_link.log.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import uuid
from pathlib import Path

DEFAULT_CHANNEL = 3
MAX_LINE = 1_000_000
NODE_ID = "hub-01"
PEER_ID = "tentacle-01"
LOG_PATH = Path(os.environ.get("NOVA_STAGING")
                or Path(__file__).resolve().parents[3] / "STAGING") / "bt_link.log"


# ---------------------------------------------------------------- framing
def make_packet(kind: str = "beacon", body="", frm: str = NODE_ID,
                to: str = PEER_ID, **extra) -> dict:
    now = time.time()
    pkt = {"v": 1, "id": f"bt-{uuid.uuid4().hex[:10]}", "kind": kind,
           "from": frm, "to": to,
           "zulu": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
           "ts": round(now, 3), "body": body}
    pkt.update(extra)
    return pkt


def encode(pkt: dict) -> bytes:
    return (json.dumps(pkt, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def decode(line: bytes) -> dict:
    obj = json.loads(line.decode("utf-8"))
    if not isinstance(obj, dict) or "kind" not in obj:
        raise ValueError("bad_packet")
    return obj


class LineReader:
    """Reads JSON-line packets from any stream socket."""

    def __init__(self, conn) -> None:
        self.conn, self.buf = conn, b""

    def read(self) -> dict | None:
        while True:
            if b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                if line.strip():
                    return decode(line)
                continue
            if len(self.buf) > MAX_LINE:
                raise ValueError("line_too_long")
            chunk = self.conn.recv(4096)
            if not chunk:
                if self.buf.strip():
                    raise ConnectionError("closed_mid_line")
                return None
            self.buf += chunk


def log_packet(pkt: dict, peer, direction: str = "rx", log_path: Path = LOG_PATH) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {direction} peer={peer} {json.dumps(pkt, ensure_ascii=False)}\n")


def handle_conn(conn, peer, node_id: str = NODE_ID, log_path: Path = LOG_PATH) -> int:
    """Read packets until EOF, log each, ack each non-ack. Returns packet count."""
    reader, n = LineReader(conn), 0
    while True:
        pkt = reader.read()
        if pkt is None:
            return n
        n += 1
        log_packet(pkt, peer, "rx", log_path)
        print(f"rx {pkt.get('kind')} from={pkt.get('from')} body={str(pkt.get('body'))[:120]!r}", flush=True)
        if pkt.get("kind") != "ack":
            conn.sendall(encode(make_packet("ack", body="ok", frm=node_id,
                                            to=str(pkt.get("from") or "?"), re=pkt.get("id"))))


# ---------------------------------------------------------------- rfcomm
def rfcomm_socket() -> socket.socket:
    if not hasattr(socket, "AF_BLUETOOTH") or not hasattr(socket, "BTPROTO_RFCOMM"):
        raise SystemExit("this Python has no socket.AF_BLUETOOTH / BTPROTO_RFCOMM")
    return socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)


def serve(channel: int = DEFAULT_CHANNEL, once: bool = False, node_id: str = NODE_ID,
          log_path: Path = LOG_PATH) -> None:
    srv = rfcomm_socket()
    try:
        srv.bind((getattr(socket, "BDADDR_ANY", "00:00:00:00:00:00"), channel))
    except OSError as exc:
        srv.close()
        raise SystemExit(f"cannot listen on RFCOMM channel {channel} ({exc}); "
                         f"it is probably taken, try --channel {channel + 1} on both sides")
    srv.listen(1)
    srv.settimeout(1.0)  # lets Ctrl+C through on Windows
    print(f"bt_link serving RFCOMM channel {channel} as {node_id}; log={log_path}", flush=True)
    try:
        while True:
            try:
                conn, peer = srv.accept()
            except socket.timeout:
                continue
            conn.settimeout(120)
            print(f"connect from {peer}", flush=True)
            try:
                with conn:
                    handle_conn(conn, peer[0] if isinstance(peer, tuple) else peer, node_id, log_path)
            except (OSError, ValueError, ConnectionError) as exc:
                print(f"conn error: {type(exc).__name__}: {exc}", flush=True)
            if once:
                return
    except KeyboardInterrupt:
        print("stopped", flush=True)
    finally:
        srv.close()


def send(addr: str, channel: int = DEFAULT_CHANNEL, kind: str = "beacon", body="",
         node_id: str = NODE_ID, peer_id: str = PEER_ID, timeout: float = 15.0,
         log_path: Path = LOG_PATH) -> dict | None:
    pkt = make_packet(kind, body, frm=node_id, to=peer_id)
    with rfcomm_socket() as s:
        s.connect((addr, channel))
        s.settimeout(timeout)
        s.sendall(encode(pkt))
        print(f"tx {kind} id={pkt['id']} -> {addr} ch{channel}", flush=True)
        ack = LineReader(s).read()
    if ack is not None:
        log_packet(ack, addr, "rx", log_path)
        print(f"rx {ack.get('kind')} re={ack.get('re')} from={ack.get('from')}", flush=True)
    else:
        print("no ack (peer closed)", flush=True)
    return ack


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m nova.mail.bt_link",
                                 description="NOVA tentacle Bluetooth RFCOMM fallback")
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("serve", "send"):
        p = sub.add_parser(name)
        p.add_argument("--channel", type=int, default=DEFAULT_CHANNEL)
        p.add_argument("--node", default=NODE_ID, help="our id (from)")
        p.add_argument("--log", type=Path, default=LOG_PATH)
        if name == "serve":
            p.add_argument("--once", action="store_true", help="exit after one connection")
        else:
            p.add_argument("--addr", required=True, help="peer Bluetooth address XX:XX:XX:XX:XX:XX")
            p.add_argument("--peer", default=PEER_ID, help="peer id (to)")
            p.add_argument("--kind", default="beacon")
            p.add_argument("--body", default="")
            p.add_argument("--timeout", type=float, default=15.0)
    a = ap.parse_args(argv)
    if a.mode == "serve":
        serve(a.channel, a.once, a.node, a.log)
        return 0
    try:
        return 0 if send(a.addr, a.channel, a.kind, a.body, a.node, a.peer, a.timeout, a.log) else 1
    except OSError as exc:
        print(f"send failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
