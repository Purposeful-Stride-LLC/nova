import os
import socket, json, time
from pathlib import Path

def open_port(host, port, t=2.0):
    s = socket.socket(); s.settimeout(t)
    try:
        s.connect((host, port)); return True
    except Exception:
        return False
    finally:
        s.close()

host = "192.168.0.76"
ports = {p: open_port(host, p) for p in (22, 11434, 41776, 41777)}
print("PORTS", json.dumps(ports))

# ICMP-ish: just note
import subprocess
ping = subprocess.run(["ping", "-n", "1", "-w", "1000", host], capture_output=True, text=True)
print("PING_OK", "TTL=" in ping.stdout or "ttl=" in ping.stdout.lower())

ssh_ok = False
prof = {}
if ports.get(22):
    try:
        import paramiko
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
        import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username="mike", password=os.environ.get("NOVA_SSH_PW", ""), timeout=15, allow_agent=False, look_for_keys=False)
        ssh_ok = True
        def run(cmd, t=90):
            _, out, err = client.exec_command(cmd, timeout=t)
            return out.read().decode("utf-8", "replace"), err.read().decode("utf-8", "replace")
        hn, _ = run("hostname")
        un, _ = run("uname -a")
        ls, _ = run("ls -la ~ | head -40")
        ol, _ = run("which ollama; ollama list 2>/dev/null | head -30; which openclaw; which node; ls /dev/video* 2>/dev/null; arecord -l 2>/dev/null | head -20")
        # deploy minimal tentacle dirs + beacon stub
        run("mkdir -p ~/nova-tentacle/{inbox,outbox,bin,log}")
        # write a tiny listen stub via heredoc
        stub = r'''#!/usr/bin/env python3
"""NOVA tentacle node — mesh beacon + mail-slot (stdlib)."""
import json, os, socket, hashlib, hmac, time, threading
from pathlib import Path
ROOT = Path.home() / "nova-tentacle"
INBOX, OUTBOX = ROOT / "inbox", ROOT / "outbox"
UDP_PORT, TCP_PORT = 41776, 41777
NODE_ID = os.environ.get("NOVA_NODE_ID", "og-ubuntu")
PSK = os.environ.get("NOVA_MESH_PSK", "change-me-homestead").encode()

def mac(body: bytes) -> str:
    return hmac.new(PSK, body, hashlib.sha256).hexdigest()[:16]

def beacon():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_PORT))
    while True:
        data, addr = sock.recvfrom(2048)
        try:
            msg = json.loads(data.decode())
        except Exception:
            continue
        if msg.get("kind") != "ping":
            continue
        pong = {"v":1,"kind":"pong","from":NODE_ID,"to":msg.get("from"),"zulu":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),"grade":"tentacle","abilities":["cpu_llm","shell","cam","mic","net"]}
        raw = json.dumps(pong, separators=(",",":")).encode()
        pong["mac"] = mac(raw)
        sock.sendto(json.dumps(pong).encode(), addr)

def mail_watch():
    """File mail-slot: inbox/*.json -> process marker in outbox."""
    while True:
        for p in INBOX.glob("*.json"):
            try:
                job = json.loads(p.read_text())
                out = {"job_id": job.get("job_id"), "ok": True, "echo": job.get("kind"), "zulu": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                (OUTBOX / (p.stem + ".result.json")).write_text(json.dumps(out, indent=2))
                p.rename(INBOX / (p.name + ".done"))
            except Exception as e:
                (OUTBOX / (p.stem + ".err.txt")).write_text(str(e))
        time.sleep(2)

if __name__ == "__main__":
    INBOX.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=beacon, daemon=True).start()
    print(f"tentacle {NODE_ID} udp:{UDP_PORT} mail:{INBOX}", flush=True)
    mail_watch()
'''
        # upload stub with sftp
        sftp = client.open_sftp()
        with sftp.file("/home/mike/nova-tentacle/bin/tentacle_node.py", "w") as f:
            f.write(stub)
        sftp.chmod("/home/mike/nova-tentacle/bin/tentacle_node.py", 0o755)
        sftp.close()
        # gather tree sample for WHI mapping later
        tree, _ = run("find ~ -maxdepth 2 -type d 2>/dev/null | head -80")
        claw, _ = run("ls -la ~/.openclaw 2>/dev/null | head -20; ls ~/openclaw 2>/dev/null | head; command -v openclaw; command -v claw")
        prof = {
            "hostname": hn.strip(),
            "uname": un.strip(),
            "home_ls": ls[:1500],
            "tools": ol[:2000],
            "tree_sample": tree[:2000],
            "claw": claw[:1000],
            "deployed": "tentacle_node.py",
            "ssh_ok": True,
        }
        client.close()
    except Exception as e:
        prof = {"ssh_ok": False, "error": type(e).__name__ + ": " + str(e)[:400]}
else:
    prof = {"ssh_ok": False, "error": "port 22 closed"}

Path("STAGING/OG_SSH_PROBE.json").write_text(json.dumps({"ports": ports, "profile": prof}, indent=2), encoding="utf-8")
print(json.dumps({"ports": ports, "ssh_ok": prof.get("ssh_ok"), "hostname": prof.get("hostname"), "error": prof.get("error"), "deployed": prof.get("deployed")}, indent=2))