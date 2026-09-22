import io, json, os, socket, stat, tarfile, time
from pathlib import Path

HOST = "192.168.0.76"
USER = "mike"
PW = "mike"
KIT = Path(r"C:\Users\wuchy\Documents\NOVA\NOVA_fieldkit_v1_4")
STAGING = KIT / "STAGING"

def port_open(host, port, t=3.0):
    s = socket.socket(); s.settimeout(t)
    try:
        s.connect((host, port)); return True
    except Exception:
        return False
    finally:
        s.close()

print("port22", port_open(HOST, 22))
print("port41776", port_open(HOST, 41776))

# --- package contents ---
NODE_PY = r'''#!/usr/bin/env python3
"""NOVA tentacle node — mesh beacon + mail-slot + metrics (stdlib)."""
from __future__ import annotations
import json, os, socket, hashlib, hmac, time, threading, traceback
from pathlib import Path

ROOT = Path(os.environ.get("NOVA_TENTACLE_ROOT", str(Path.home() / "pg" / "nova-tentacle"))).expanduser()
INBOX, OUTBOX, LOG = ROOT / "inbox", ROOT / "outbox", ROOT / "log"
UDP_PORT = int(os.environ.get("NOVA_MESH_UDP", "41776"))
TCP_PORT = int(os.environ.get("NOVA_MESH_TCP", "41777"))
NODE_ID = os.environ.get("NOVA_NODE_ID", "og-ubuntu")
PSK = os.environ.get("NOVA_MESH_PSK", "change-me-homestead").encode()
METRICS = LOG / "metrics.jsonl"

def zulu():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def mac(body: bytes) -> str:
    return hmac.new(PSK, body, hashlib.sha256).hexdigest()[:16]

def log_metric(kind: str, **kw):
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    row = {"zulu": zulu(), "kind": kind, **kw}
    with METRICS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")

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

def beacon():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_PORT))
    log_metric("beacon_bind", port=UDP_PORT)
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            msg = json.loads(data.decode("utf-8", "replace"))
            if msg.get("kind") != "ping":
                continue
            pong = {
                "v": 1,
                "kind": "pong",
                "from": NODE_ID,
                "to": msg.get("from"),
                "zulu": zulu(),
                "grade": "tentacle",
                "abilities": abilities(),
                "load": load_avg(),
                "mem": meminfo(),
            }
            raw = json.dumps({k: pong[k] for k in pong if k != "mac"}, separators=(",", ":")).encode()
            pong["mac"] = mac(raw)
            sock.sendto(json.dumps(pong).encode(), addr)
            log_metric("pong", peer=addr[0], load=pong.get("load"))
        except Exception as e:
            log_metric("beacon_err", error=str(e)[:200])
            time.sleep(0.5)

def handle_job(job: dict) -> dict:
    kind = (job.get("kind") or job.get("body") or "ping").split()[0]
    if kind in ("ping", "health"):
        return {"ok": True, "kind": kind, "load": load_avg(), "mem": meminfo(), "abilities": abilities()}
    if kind == "map_fs":
        root = Path(job.get("path") or str(Path.home()))
        depth = int(job.get("depth") or 2)
        rows = []
        base_len = len(root.parts)
        for p in root.rglob("*"):
            try:
                if len(p.parts) - base_len > depth:
                    continue
                rows.append({"path": str(p), "dir": p.is_dir(), "size": (p.stat().st_size if p.is_file() else 0)})
                if len(rows) >= int(job.get("limit") or 200):
                    break
            except Exception:
                continue
        return {"ok": True, "kind": "map_fs", "n": len(rows), "rows": rows}
    if kind == "discover":
        info = {
            "hostname": socket.gethostname(),
            "cwd": os.getcwd(),
            "home": str(Path.home()),
            "abilities": abilities(),
            "load": load_avg(),
            "mem": meminfo(),
            "has_ollama": bool(__import__("shutil").which("ollama")),
            "has_openclaw": bool(__import__("shutil").which("openclaw")),
            "videos": [str(p) for p in Path("/dev").glob("video*")],
        }
        try:
            import subprocess
            if info["has_ollama"]:
                info["ollama_list"] = subprocess.check_output(["ollama", "list"], text=True, timeout=60)[:2000]
        except Exception as e:
            info["ollama_err"] = str(e)[:200]
        return {"ok": True, "kind": "discover", "info": info}
    return {"ok": False, "error": f"unknown_kind:{kind}"}

def mail_watch():
    while True:
        for p in list(INBOX.glob("*.json")):
            try:
                job = json.loads(p.read_text(encoding="utf-8"))
                t0 = time.time()
                result = handle_job(job)
                result["job_id"] = job.get("job_id") or p.stem
                result["ms"] = int((time.time() - t0) * 1000)
                result["zulu"] = zulu()
                (OUTBOX / f"{p.stem}.result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
                p.rename(INBOX / (p.name + ".done"))
                log_metric("job", job_id=result["job_id"], kind=job.get("kind"), ok=result.get("ok"), ms=result.get("ms"))
            except Exception as e:
                (OUTBOX / f"{p.stem}.err.txt").write_text(traceback.format_exc()[:2000], encoding="utf-8")
                log_metric("job_err", file=p.name, error=str(e)[:200])
                try:
                    p.rename(INBOX / (p.name + ".err"))
                except Exception:
                    pass
        time.sleep(1.0)

def main():
    for d in (INBOX, OUTBOX, LOG, ROOT / "bin"):
        d.mkdir(parents=True, exist_ok=True)
    (ROOT / "NODE_ID").write_text(NODE_ID + "\n", encoding="utf-8")
    threading.Thread(target=beacon, daemon=True).start()
    log_metric("start", node=NODE_ID, root=str(ROOT), udp=UDP_PORT, tcp=TCP_PORT)
    print(f"tentacle {NODE_ID} root={ROOT} udp={UDP_PORT}", flush=True)
    # self discover once
    disc = handle_job({"kind": "discover", "job_id": "boot-discover"})
    (OUTBOX / "boot-discover.result.json").write_text(json.dumps(disc, indent=2), encoding="utf-8")
    mail_watch()

if __name__ == "__main__":
    main()
'''

README = """# nova-tentacle (OG Ubuntu node)

Mesh: UDP 41776 ping/pong. Mail-slot: inbox/*.json -> outbox/*.result.json

Start:
  cd ~/pg/nova-tentacle
  NOVA_NODE_ID=og-ubuntu python3 bin/tentacle_node.py

Or:
  bash bin/start.sh
"""

START_SH = """#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NOVA_TENTACLE_ROOT="$ROOT"
export NOVA_NODE_ID="${NOVA_NODE_ID:-og-ubuntu}"
export NOVA_MESH_UDP="${NOVA_MESH_UDP:-41776}"
mkdir -p "$ROOT/log"
cd "$ROOT"
nohup python3 bin/tentacle_node.py >> log/tentacle.stdout 2>> log/tentacle.stderr &
echo $! > log/tentacle.pid
echo "started pid=$(cat log/tentacle.pid) root=$ROOT"
"""

# write local tar.gz
pkg_dir = STAGING / "_tentacle_pkg"
if pkg_dir.exists():
    import shutil
    shutil.rmtree(pkg_dir)
(pkg_dir / "bin").mkdir(parents=True)
(pkg_dir / "inbox").mkdir()
(pkg_dir / "outbox").mkdir()
(pkg_dir / "log").mkdir()
(pkg_dir / "bin" / "tentacle_node.py").write_text(NODE_PY, encoding="utf-8")
(pkg_dir / "bin" / "start.sh").write_text(START_SH.replace("\r\n", "\n"), encoding="utf-8")
(pkg_dir / "README.md").write_text(README, encoding="utf-8")
(pkg_dir / "MESH.json").write_text(json.dumps({"udp": 41776, "tcp": 41777, "node_id": "og-ubuntu", "grade": "tentacle"}, indent=2), encoding="utf-8")

tar_path = STAGING / "nova-tentacle-og.tar.gz"
with tarfile.open(tar_path, "w:gz") as tar:
    for p in pkg_dir.rglob("*"):
        if p.is_file():
            tar.add(p, arcname=str(Path("nova-tentacle") / p.relative_to(pkg_dir)).replace("\\", "/"))
print("built", tar_path, tar_path.stat().st_size)

if not port_open(HOST, 22):
    raise SystemExit("SSH still closed on :22")

import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PW, timeout=20, allow_agent=False, look_for_keys=False)

def run(cmd, t=120):
    _, out, err = client.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", "replace"), err.read().decode("utf-8", "replace"), out.channel.recv_exit_status()

# find pg folder
find_out, find_err, _ = run("hostname; whoami; ls -la ~; ls -la ~/pg 2>/dev/null; ls -la /home/mike/pg 2>/dev/null; find /home/mike -maxdepth 3 -type d -name pg 2>/dev/null; find / -maxdepth 3 -type d -name pg 2>/dev/null | head -20")
print("FIND<<<"); print(find_out[:2500]); print("ERR", find_err[:500]); print(">>>")

# prefer ~/pg then create
run("mkdir -p ~/pg")
remote_tar = "/home/mike/pg/nova-tentacle-og.tar.gz"
remote_root = "/home/mike/pg/nova-tentacle"

sftp = client.open_sftp()
sftp.put(str(tar_path), remote_tar)
sftp.close()
print("uploaded", remote_tar)

# unpack + launch
out, err, rc = run(f"cd /home/mike/pg && rm -rf nova-tentacle && tar -xzf nova-tentacle-og.tar.gz && chmod +x nova-tentacle/bin/start.sh nova-tentacle/bin/tentacle_node.py && bash nova-tentacle/bin/start.sh")
print("START rc", rc); print(out); print(err)

time.sleep(2)
out2, err2, _ = run("cat ~/pg/nova-tentacle/log/tentacle.pid 2>/dev/null; ps -p $(cat ~/pg/nova-tentacle/log/tentacle.pid 2>/dev/null) -o pid,cmd 2>/dev/null; tail -20 ~/pg/nova-tentacle/log/tentacle.stdout 2>/dev/null; tail -20 ~/pg/nova-tentacle/log/metrics.jsonl 2>/dev/null; cat ~/pg/nova-tentacle/outbox/boot-discover.result.json 2>/dev/null | head -80")
print("STATUS<<<"); print(out2[:3000]); print(err2[:500]); print(">>>")

# drop a discover job via mail-slot too
job = {"job_id": "hub-discover-1", "kind": "discover", "from": "hub:tuf"}
run("cat > ~/pg/nova-tentacle/inbox/hub-discover-1.json << 'EOF'\n" + json.dumps(job) + "\nEOF")
time.sleep(2)
out3, _, _ = run("cat ~/pg/nova-tentacle/outbox/hub-discover-1.result.json 2>/dev/null; tail -5 ~/pg/nova-tentacle/log/metrics.jsonl")
print("JOB<<<"); print(out3[:2000]); print(">>>")

# firewall note — may need ufw allow
out4, _, _ = run("command -v ufw >/dev/null && sudo -n ufw status 2>/dev/null || echo no-ufw-or-no-sudo; ss -ulnp | grep 41776 || netstat -ulnp 2>/dev/null | grep 41776 || echo 'udp41776 not shown'")
print("NET<<<"); print(out4[:1000]); print(">>>")

client.close()

# hub-side ping attempt
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)
ping = {"v":1,"kind":"ping","from":"hub:tuf","to":"og-ubuntu","zulu":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
sock.sendto(json.dumps(ping).encode(), (HOST, 41776))
try:
    data, addr = sock.recvfrom(4096)
    print("PONG", data[:500])
except Exception as e:
    print("PONG_FAIL", type(e).__name__, e)

report = {
    "ssh_ok": True,
    "remote_root": remote_root,
    "tar": str(tar_path),
    "deploy": "tar.gz via sftp into ~/pg",
}
(STAGING / "OG_TENTACLE_DEPLOY.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("DONE", report)