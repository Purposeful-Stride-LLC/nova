#!/usr/bin/env python3
"""NOVA tentacle — TCP mail: 41776 beacon, 41777 jobs (firewall TCP)."""
from __future__ import annotations
import json, os, socket, hashlib, hmac, time, threading, traceback, subprocess, shutil, struct
from pathlib import Path

ROOT = Path(os.environ.get("NOVA_TENTACLE_ROOT", str(Path.home() / "pg" / "nova-tentacle"))).expanduser()
INBOX, OUTBOX, LOG = ROOT / "inbox", ROOT / "outbox", ROOT / "log"
TCP_BEACON = int(os.environ.get("NOVA_MESH_TCP_BEACON", os.environ.get("NOVA_MESH_UDP", "41776")))
TCP_JOB = int(os.environ.get("NOVA_MESH_TCP_JOB", os.environ.get("NOVA_MESH_JOB_UDP", "41777")))
NODE_ID = os.environ.get("NOVA_NODE_ID", "og-ubuntu")
PSK = os.environ.get("NOVA_MESH_PSK", "change-me-homestead").encode()
METRICS = LOG / "metrics.jsonl"
MAX_FRAME = 8_000_000

def zulu():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def mac(body: bytes) -> str:
    return hmac.new(PSK, body, hashlib.sha256).hexdigest()[:16]

def log_metric(event: str, **kw):
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    with METRICS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"zulu": zulu(), "kind": event, **kw}) + "\n")

def load_avg():
    try:
        with open("/proc/loadavg") as f:
            a, b, c, *_ = f.read().split()
        return {"load1": float(a), "load5": float(b), "load15": float(c)}
    except Exception:
        return {}

def meminfo():
    out = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith(("MemTotal:", "MemAvailable:")):
                    k, v, *_ = line.split()
                    out[k[:-1]] = int(v)
    except Exception:
        pass
    return out

def abilities():
    abs_ = ["cpu_llm", "shell", "net", "fs_map"]
    if any(Path("/dev").glob("video*")):
        abs_.append("cam")
    if Path("/dev/snd").exists() or Path("/proc/asound").exists():
        abs_.append("mic")
    return abs_

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
    if len(raw) > MAX_FRAME:
        jid = obj.get("job_id") or "job"
        path = OUTBOX / f"{jid}.result.json"
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        obj = {"ok": True, "overflow": True, "path": str(path), "job_id": jid, "ms": obj.get("ms")}
        raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    conn.sendall(struct.pack("!I", len(raw)) + raw)

def handle_job(job: dict) -> dict:
    t0 = time.perf_counter()
    kind = (job.get("kind") or "ping").split()[0]
    out = {"ok": False, "kind": kind}
    try:
        if kind in ("ping", "health"):
            out.update({"ok": True, "load": load_avg(), "mem": meminfo(), "abilities": abilities(), "proto": "tcp"})
        elif kind == "discover":
            info = {
                "hostname": socket.gethostname(),
                "abilities": abilities(),
                "load": load_avg(),
                "mem": meminfo(),
                "has_ollama": bool(shutil.which("ollama")),
                "videos": [str(p) for p in Path("/dev").glob("video*")],
                "proto": {"beacon_tcp": TCP_BEACON, "job_tcp": TCP_JOB},
            }
            if info["has_ollama"]:
                try:
                    info["ollama_list"] = subprocess.check_output(["ollama", "list"], text=True, timeout=90)[:2500]
                except Exception as e:
                    info["ollama_err"] = str(e)[:200]
            out.update({"ok": True, "info": info})
        elif kind == "map_fs":
            root = Path(job.get("path") or str(Path.home()))
            depth = int(job.get("depth") or 2)
            limit = int(job.get("limit") or 200)
            rows = []
            base = len(root.parts)
            for p in root.rglob("*"):
                try:
                    if len(p.parts) - base > depth:
                        continue
                    rows.append({"path": str(p), "dir": p.is_dir(), "size": (p.stat().st_size if p.is_file() else 0)})
                    if len(rows) >= limit:
                        break
                except Exception:
                    continue
            out.update({"ok": True, "n": len(rows), "rows": rows})
        elif kind == "ollama_gen":
            model = job.get("model") or "qwen:0.5b"
            prompt = job.get("prompt") or "Say pong in five words."
            p = subprocess.run(
                ["ollama", "run", model, prompt],
                capture_output=True, text=True, timeout=int(job.get("timeout") or 300),
            )
            out.update({"ok": p.returncode == 0, "model": model, "stdout": (p.stdout or "")[:2000], "stderr": (p.stderr or "")[:500], "rc": p.returncode})
        elif kind == "apt_inventory":
            pkgs = subprocess.check_output(["dpkg", "--get-selections"], text=True, timeout=60)
            lines = [ln.split()[0] for ln in pkgs.splitlines() if ln.strip().endswith("install")]
            keys = ("python", "ffmpeg", "gimp", "inkscape", "audacity", "vlc", "curl", "wget", "git", "opencv", "tesseract", "libreoffice", "imagemagick", "sox", "pandoc", "nmap", "docker", "nodejs", "npm", "obs", "cheese", "shotwell", "blender", "freecad")
            interesting = [p for p in lines if any(k in p for k in keys)]
            desktop = []
            for d in [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]:
                if d.exists():
                    desktop.extend([x.name for x in d.glob("*.desktop")][:80])
            out.update({"ok": True, "n_pkgs": len(lines), "interesting": interesting[:120], "desktop_sample": desktop[:80]})
        elif kind == "which_tools":
            names = job.get("names") or ["python3", "ffmpeg", "curl", "git", "ollama", "freecad"]
            out.update({"ok": True, "which": {n: (shutil.which(n) or "") for n in names}})
        elif kind == "sys_inventory":
            # reuse discover + which + short uname
            disc = handle_job({"kind": "discover", "job_id": job.get("job_id")})
            which = handle_job({"kind": "which_tools", "job_id": job.get("job_id")})
            out.update({"ok": True, "discover": disc.get("info"), "which": which.get("which"), "uname": os.uname()._asdict() if hasattr(os, "uname") else {}})
        else:
            out["error"] = f"unknown_kind:{kind}"
    except Exception as e:
        out["error"] = str(e)[:400]
        out["trace"] = traceback.format_exc()[:800]
    out["ms"] = int((time.perf_counter() - t0) * 1000)
    out["zulu"] = zulu()
    out["job_id"] = job.get("job_id")
    out["load_after"] = load_avg()
    return out

def serve_tcp(port: int, mode: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(16)
    log_metric("tcp_bind", port=port, mode=mode)
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_conn, args=(conn, addr, mode), daemon=True).start()

def handle_conn(conn: socket.socket, addr, mode: str):
    try:
        conn.settimeout(120)
        msg = recv_frame(conn)
        if mode == "beacon":
            if msg.get("kind") != "ping":
                send_frame(conn, {"ok": False, "error": "expected_ping"})
                return
            pong = {
                "v": 1, "kind": "pong", "from": NODE_ID, "to": msg.get("from"), "zulu": zulu(),
                "grade": "tentacle", "abilities": abilities(), "load": load_avg(), "mem": meminfo(),
                "job_tcp": TCP_JOB, "beacon_tcp": TCP_BEACON, "proto": "tcp",
            }
            raw = json.dumps({k: pong[k] for k in pong}, separators=(",", ":")).encode()
            pong["mac"] = mac(raw)
            send_frame(conn, pong)
            log_metric("pong", peer=addr[0], load=pong.get("load"))
        else:
            job = msg if msg.get("kind") else {**msg, "kind": "ping"}
            result = handle_job(job)
            send_frame(conn, result)
            log_metric("job", job_id=result.get("job_id"), job_kind=job.get("kind"), ok=result.get("ok"), ms=result.get("ms"), peer=addr[0], via="tcp")
    except Exception as e:
        log_metric("tcp_err", mode=mode, error=str(e)[:200], peer=str(addr))
        try:
            send_frame(conn, {"ok": False, "error": str(e)[:300]})
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def mail_watch():
    while True:
        for p in list(INBOX.glob("*.json")):
            try:
                job = json.loads(p.read_text(encoding="utf-8"))
                result = handle_job(job)
                (OUTBOX / f"{p.stem}.result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
                p.rename(INBOX / (p.name + ".done"))
                log_metric("job", job_id=result.get("job_id"), job_kind=job.get("kind"), ok=result.get("ok"), ms=result.get("ms"), via="mail")
            except Exception as e:
                (OUTBOX / f"{p.stem}.err.txt").write_text(traceback.format_exc()[:2000], encoding="utf-8")
                try:
                    p.rename(INBOX / (p.name + ".err"))
                except Exception:
                    pass
        time.sleep(1)

def main():
    for d in (INBOX, OUTBOX, LOG):
        d.mkdir(parents=True, exist_ok=True)
    (ROOT / "NODE_ID").write_text(NODE_ID + "\n", encoding="utf-8")
    (ROOT / "MESH.json").write_text(json.dumps({
        "beacon_tcp": TCP_BEACON, "job_tcp": TCP_JOB, "proto": "tcp",
        "node_id": NODE_ID, "grade": "tentacle",
    }, indent=2) + "\n", encoding="utf-8")
    threading.Thread(target=serve_tcp, args=(TCP_BEACON, "beacon"), daemon=True).start()
    threading.Thread(target=serve_tcp, args=(TCP_JOB, "job"), daemon=True).start()
    log_metric("start", node=NODE_ID, beacon_tcp=TCP_BEACON, job_tcp=TCP_JOB, proto="tcp")
    print(f"tentacle {NODE_ID} beacon_tcp={TCP_BEACON} job_tcp={TCP_JOB}", flush=True)
    mail_watch()

if __name__ == "__main__":
    main()
