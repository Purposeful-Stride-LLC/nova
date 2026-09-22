import json, socket, time, signal, os, subprocess, shutil, traceback, threading, hashlib, hmac
from pathlib import Path
import paramiko

HOST, USER, PW = "192.168.0.76", "mike", "mike"
STAGING = Path(r"C:\Users\wuchy\Documents\NOVA\NOVA_fieldkit_v1_4\STAGING")
REMOTE_ROOT = "/home/mike/pg/nova-tentacle"

NODE_SRC = r'''#!/usr/bin/env python3
"""NOVA tentacle — dual UDP: 41776 beacon, 41777 job."""
from __future__ import annotations
import json, os, socket, hashlib, hmac, time, threading, traceback, subprocess, shutil
from pathlib import Path

ROOT = Path(os.environ.get("NOVA_TENTACLE_ROOT", str(Path.home() / "pg" / "nova-tentacle"))).expanduser()
INBOX, OUTBOX, LOG = ROOT / "inbox", ROOT / "outbox", ROOT / "log"
UDP_BEACON = int(os.environ.get("NOVA_MESH_UDP", "41776"))
UDP_JOB = int(os.environ.get("NOVA_MESH_JOB_UDP", "41777"))
NODE_ID = os.environ.get("NOVA_NODE_ID", "og-ubuntu")
PSK = os.environ.get("NOVA_MESH_PSK", "change-me-homestead").encode()
METRICS = LOG / "metrics.jsonl"

def zulu():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def mac(body: bytes) -> str:
    return hmac.new(PSK, body, hashlib.sha256).hexdigest()[:16]

def log_metric(event: str, **kw):
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    row = {"zulu": zulu(), "kind": event, **kw}
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

def handle_job(job: dict) -> dict:
    t0 = time.perf_counter()
    kind = (job.get("kind") or "ping").split()[0]
    out = {"ok": False, "kind": kind}
    try:
        if kind in ("ping", "health"):
            out.update({"ok": True, "load": load_avg(), "mem": meminfo(), "abilities": abilities()})
        elif kind == "discover":
            info = {
                "hostname": socket.gethostname(),
                "abilities": abilities(),
                "load": load_avg(),
                "mem": meminfo(),
                "has_ollama": bool(shutil.which("ollama")),
                "videos": [str(p) for p in Path("/dev").glob("video*")],
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
                capture_output=True,
                text=True,
                timeout=int(job.get("timeout") or 300),
            )
            out.update({
                "ok": p.returncode == 0,
                "model": model,
                "stdout": (p.stdout or "")[:2000],
                "stderr": (p.stderr or "")[:500],
                "rc": p.returncode,
            })
        elif kind == "apt_inventory":
            pkgs = subprocess.check_output(["dpkg", "--get-selections"], text=True, timeout=60)
            lines = [ln.split()[0] for ln in pkgs.splitlines() if ln.strip().endswith("install")]
            keys = (
                "python", "ffmpeg", "gimp", "inkscape", "audacity", "vlc", "curl", "wget",
                "git", "opencv", "tesseract", "libreoffice", "imagemagick", "sox", "pandoc",
                "nmap", "wireshark", "docker", "nodejs", "npm", "obs", "cheese",
                "shotwell", "blender", "freecad", "gnuradio", "fldigi",
            )
            interesting = [p for p in lines if any(k in p for k in keys)]
            desktop = []
            for d in [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]:
                if d.exists():
                    desktop.extend([x.name for x in d.glob("*.desktop")][:80])
            out.update({"ok": True, "n_pkgs": len(lines), "interesting": interesting[:120], "desktop_sample": desktop[:80]})
        elif kind == "which_tools":
            names = job.get("names") or [
                "python3", "ffmpeg", "convert", "gimp", "inkscape", "audacity", "vlc",
                "curl", "git", "tesseract", "pandoc", "nmap", "docker", "node", "obs",
                "cheese", "soffice", "sox", "wget",
            ]
            found = {n: (shutil.which(n) or "") for n in names}
            out.update({"ok": True, "which": found})
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

def beacon_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_BEACON))
    log_metric("beacon_bind", port=UDP_BEACON)
    while True:
        try:
            data, addr = sock.recvfrom(8192)
            msg = json.loads(data.decode("utf-8", "replace"))
            if msg.get("kind") != "ping":
                continue
            pong = {
                "v": 1, "kind": "pong", "from": NODE_ID, "to": msg.get("from"), "zulu": zulu(),
                "grade": "tentacle", "abilities": abilities(), "load": load_avg(), "mem": meminfo(),
                "job_udp": UDP_JOB,
            }
            raw = json.dumps({k: pong[k] for k in pong}, separators=(",", ":")).encode()
            pong["mac"] = mac(raw)
            sock.sendto(json.dumps(pong).encode(), addr)
            log_metric("pong", peer=addr[0], load=pong.get("load"))
        except Exception as e:
            log_metric("beacon_err", error=str(e)[:200])
            time.sleep(0.2)

def job_udp_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_JOB))
    log_metric("job_udp_bind", port=UDP_JOB)
    while True:
        try:
            data, addr = sock.recvfrom(65535)
            job = json.loads(data.decode("utf-8", "replace"))
            result = handle_job(job if job.get("kind") else {**job, "kind": "ping"})
            raw = json.dumps(result).encode()
            if len(raw) > 50000:
                jid = result.get("job_id") or "job"
                path = OUTBOX / f"{jid}.result.json"
                path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                result = {"ok": True, "overflow": True, "path": str(path), "job_id": jid, "ms": result.get("ms")}
                raw = json.dumps(result).encode()
            sock.sendto(raw, addr)
            log_metric("job", job_id=result.get("job_id"), job_kind=job.get("kind"), ok=result.get("ok"), ms=result.get("ms"), peer=addr[0])
        except Exception as e:
            log_metric("job_udp_err", error=str(e)[:200])
            try:
                sock.sendto(json.dumps({"ok": False, "error": str(e)[:300]}).encode(), addr)
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
                log_metric("job_err", file=p.name, error=str(e)[:200])
                try:
                    p.rename(INBOX / (p.name + ".err"))
                except Exception:
                    pass
        time.sleep(1)

def main():
    for d in (INBOX, OUTBOX, LOG):
        d.mkdir(parents=True, exist_ok=True)
    (ROOT / "NODE_ID").write_text(NODE_ID + "\n", encoding="utf-8")
    threading.Thread(target=beacon_loop, daemon=True).start()
    threading.Thread(target=job_udp_loop, daemon=True).start()
    log_metric("start", node=NODE_ID, root=str(ROOT), udp_beacon=UDP_BEACON, udp_job=UDP_JOB)
    print(f"tentacle {NODE_ID} beacon={UDP_BEACON} job_udp={UDP_JOB}", flush=True)
    mail_watch()

if __name__ == "__main__":
    main()
'''


def udp_exchange(port, payload, wait=3.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(wait)
    t0 = time.perf_counter()
    sock.sendto(json.dumps(payload).encode(), (HOST, port))
    try:
        data, _ = sock.recvfrom(65535)
        ms = (time.perf_counter() - t0) * 1000
        return {"ok": True, "ms": round(ms, 1), "bytes": len(data), "data": data.decode("utf-8", "replace")}
    except Exception as e:
        return {"ok": False, "ms": round((time.perf_counter() - t0) * 1000, 1), "error": f"{type(e).__name__}: {e}"}
    finally:
        sock.close()


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PW, timeout=20, allow_agent=False, look_for_keys=False)

    def run(cmd, t=120):
        _, out, err = client.exec_command(cmd, timeout=t)
        return out.read().decode("utf-8", "replace"), err.read().decode("utf-8", "replace"), out.channel.recv_exit_status()

    sftp = client.open_sftp()
    with sftp.file(f"{REMOTE_ROOT}/bin/tentacle_node.py", "w") as f:
        f.write(NODE_SRC)
    sftp.close()

    # restart via remote python (avoid local PS $())
    restart = f"""
python3 - <<'PY'
from pathlib import Path
import os, signal, time, subprocess
pidf = Path('{REMOTE_ROOT}/log/tentacle.pid')
if pidf.exists():
    try:
        os.kill(int(pidf.read_text().strip()), signal.SIGTERM)
        time.sleep(1)
    except Exception as e:
        print('kill', e)
subprocess.check_call(['bash', '{REMOTE_ROOT}/bin/start.sh'])
print('pid', pidf.read_text().strip())
PY
"""
    out, err, rc = run(restart)
    print("RESTART", rc, out.strip(), err[:200])
    time.sleep(1.5)

    matrix = []
    tests = [
        {"job_id": "t-ping", "kind": "ping"},
        {"job_id": "t-which", "kind": "which_tools"},
        {"job_id": "t-apt", "kind": "apt_inventory"},
        {"job_id": "t-map", "kind": "map_fs", "path": "/home/mike/pg", "depth": 2, "limit": 80},
        {"job_id": "t-ollama", "kind": "ollama_gen", "model": "qwen:0.5b", "prompt": "Reply with exactly: NODE_PONG_OK", "timeout": 240},
    ]
    for job in tests:
        wait = 240.0 if job["kind"] == "ollama_gen" else 45.0
        print("RUN", job["job_id"], "...")
        r = udp_exchange(41777, job, wait=wait)
        entry = {"job": job["job_id"], "kind": job["kind"], "udp_ok": r.get("ok"), "rtt_ms": r.get("ms"), "error": r.get("error")}
        if r.get("ok"):
            try:
                body = json.loads(r["data"])
                entry["job_ms"] = body.get("ms")
                entry["ok"] = body.get("ok")
                entry["load_after"] = body.get("load_after")
                entry["overflow"] = body.get("overflow")
                if job["kind"] == "ollama_gen":
                    entry["stdout_snip"] = (body.get("stdout") or "")[:160]
                    entry["model"] = body.get("model")
                    entry["stderr_snip"] = (body.get("stderr") or "")[:160]
                if job["kind"] == "apt_inventory":
                    if body.get("overflow"):
                        # fetch via sftp
                        sftp_open = client.open_sftp()
                        try:
                            pth = body.get("path") or f"{REMOTE_ROOT}/outbox/{job['job_id']}.result.json"
                            try:
                                with sftp_open.file(pth, "r") as fh:
                                    body = json.loads(fh.read().decode())
                            except Exception as e:
                                entry["overflow_fetch_err"] = str(e)
                        finally:
                            sftp_open.close()
                    entry["n_pkgs"] = body.get("n_pkgs")
                    entry["interesting"] = (body.get("interesting") or [])[:50]
                    entry["desktop_sample"] = (body.get("desktop_sample") or [])[:40]
                if job["kind"] == "which_tools":
                    entry["which"] = body.get("which")
                if job["kind"] == "map_fs":
                    entry["n"] = body.get("n")
            except Exception as e:
                entry["parse_err"] = str(e)
                entry["raw"] = (r.get("data") or "")[:240]
        matrix.append(entry)
        print(json.dumps({k: entry[k] for k in entry if k not in ("interesting", "desktop_sample", "which")}, default=str))

    beacon_times = []
    for i in range(5):
        r = udp_exchange(41776, {"v": 1, "kind": "ping", "from": "hub:tuf", "n": i}, wait=2)
        beacon_times.append(r.get("ms"))
    print("beacon_rtt_ms", beacon_times)

    # pull metrics tail
    sftp = client.open_sftp()
    try:
        with sftp.file(f"{REMOTE_ROOT}/log/metrics.jsonl", "r") as fh:
            lines = fh.read().decode("utf-8", "replace").splitlines()[-20:]
    except Exception:
        lines = []
    sftp.close()
    client.close()

    # API hook ideas from which/interesting
    hooks = []
    wh = next((m.get("which") for m in matrix if m.get("kind") == "which_tools"), {}) or {}
    interest = next((m.get("interesting") for m in matrix if m.get("kind") == "apt_inventory"), []) or []
    if wh.get("ffmpeg") or any("ffmpeg" in x for x in interest):
        hooks.append({"app": "ffmpeg", "api": "subprocess / python-ffmpeg", "use": "cam preprocess, clip cut, scout video"})
    if wh.get("gimp") or any("gimp" in x for x in interest):
        hooks.append({"app": "gimp", "api": "gimp-console batch / python-fu", "use": "image toolbox pet (CPU)"})
    if wh.get("convert") or any("imagemagick" in x for x in interest):
        hooks.append({"app": "ImageMagick", "api": "convert CLI", "use": "thumbnails, format normalize"})
    if wh.get("tesseract") or any("tesseract" in x for x in interest):
        hooks.append({"app": "tesseract", "api": "pytesseract / CLI", "use": "OCR scout"})
    if wh.get("curl"):
        hooks.append({"app": "curl", "api": "CLI", "use": "hunter HTTP fetch (HIL)"})
    if wh.get("nmap") or any("nmap" in x for x in interest):
        hooks.append({"app": "nmap", "api": "CLI", "use": "LAN map assist (HIL)"})
    if any("freecad" in x for x in interest):
        hooks.append({"app": "FreeCAD", "api": "FreeCAD cmd / Python", "use": "CAD docs already in AiTutor roots"})
    if any("gnuradio" in x or "fldigi" in x for x in interest):
        hooks.append({"app": "gnuradio/fldigi", "api": "native Linux RF stack", "use": "homestead RF explore later"})
    if wh.get("python3"):
        hooks.append({"app": "python3", "api": "stdlib + venv", "use": "tentacle core, digester glue"})
    hooks.append({"app": "ollama", "api": "CLI/HTTP :11434 local", "use": "CPU chronicler digester / scout summarize"})

    report = {
        "zulu": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "channel": {"41776": "UDP beacon duplex ping/pong", "41777": "UDP job duplex (adapted from TCP plan)"},
        "beacon_rtt_ms": beacon_times,
        "matrix": matrix,
        "python_api_hooks": hooks,
        "metrics_tail": lines,
        "slave_thesis": "OG offloads digest/scout/preprocess; TUF keeps GPU speak/Claw/palace truth",
    }
    STAGING.joinpath("OG_TENTACLE_TEST_MATRIX.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    STAGING.joinpath("OG_LINUX_API_HOOKS.md").write_text(
        "# LinuxBox1 Python/API hooks for tentacle\n\n"
        + "\n".join(f"- **{h['app']}**: {h['api']} — {h['use']}" for h in hooks)
        + "\n",
        encoding="utf-8",
    )
    print("DONE matrix file written")


if __name__ == "__main__":
    main()
