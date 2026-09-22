"""Windows metal probes. Prefer psutil; fall back gracefully."""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import urllib.request
from pathlib import Path

import psutil

from nova.db import zulu


def _base(source: str, **extra) -> dict:
    row = {"source": source, "ok": True, "zulu": zulu(), "os": platform.system()}
    row.update(extra)
    return row


def hardware() -> dict:
    vm = psutil.virtual_memory()
    cpu_freq = None
    try:
        f = psutil.cpu_freq()
        cpu_freq = {"current": getattr(f, "current", None), "max": getattr(f, "max", None)}
    except Exception:
        pass
    battery = None
    try:
        b = psutil.sensors_battery()
        if b:
            battery = {"percent": b.percent, "plugged": b.power_plugged}
    except Exception:
        pass
    return _base(
        "hardware",
        hostname=socket.gethostname(),
        platform=platform.platform(),
        processor=platform.processor(),
        machine=platform.machine(),
        cpu_logical=psutil.cpu_count(logical=True),
        cpu_physical=psutil.cpu_count(logical=False),
        cpu_percent=psutil.cpu_percent(interval=0.2),
        cpu_freq=cpu_freq,
        ram_total_gb=round(vm.total / (1024**3), 2),
        ram_used_gb=round(vm.used / (1024**3), 2),
        ram_percent=vm.percent,
        battery=battery,
    )


def process() -> dict:
    """Top CPU/RSS processes — Windows-friendly via psutil."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "username"]):
        try:
            info = p.info
            mem = info.get("memory_info")
            rss = int(getattr(mem, "rss", 0) or 0)
            procs.append(
                {
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "cpu": info.get("cpu_percent") or 0.0,
                    "rss_mb": round(rss / (1024**2), 1),
                    "user": info.get("username"),
                }
            )
        except (psutil.Error, TypeError, ValueError):
            continue
    # warm cpu_percent
    psutil.cpu_percent(interval=0.15)
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            mem = info.get("memory_info")
            rss = int(getattr(mem, "rss", 0) or 0)
            for row in procs:
                if row["pid"] == info.get("pid"):
                    row["cpu"] = info.get("cpu_percent") or 0.0
                    row["rss_mb"] = round(rss / (1024**2), 1)
        except (psutil.Error, TypeError, ValueError):
            continue
    top_cpu = sorted(procs, key=lambda r: r.get("cpu") or 0, reverse=True)[:12]
    top_rss = sorted(procs, key=lambda r: r.get("rss_mb") or 0, reverse=True)[:12]
    interesting = []
    for name in ("ollama", "python", "openclaw", "node", "pocket"):
        hits = [r for r in procs if name.lower() in (r.get("name") or "").lower()]
        if hits:
            interesting.append({"match": name, "n": len(hits), "sample": hits[:3]})
    return _base(
        "process",
        n_processes=len(procs),
        top_cpu=top_cpu,
        top_rss=top_rss,
        interesting=interesting,
    )


def network() -> dict:
    addrs = {}
    for iface, lst in psutil.net_if_addrs().items():
        addrs[iface] = [
            {"family": str(a.family), "address": a.address, "netmask": a.netmask}
            for a in lst
            if a.address
        ]
    stats = {}
    for iface, st in psutil.net_if_stats().items():
        stats[iface] = {"up": st.isup, "speed": st.speed}
    io = psutil.net_io_counters()
    return _base(
        "network",
        hostname=socket.gethostname(),
        interfaces=addrs,
        iface_stats=stats,
        bytes_sent=io.bytes_sent,
        bytes_recv=io.bytes_recv,
    )


def lan() -> dict:
    """LAN glance: default route-ish via UDP trick + ping gateway optional."""
    local_ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception as exc:
        return _base("lan", ok=False, error=str(exc), local_ip=None)
    # Windows: route print parse is heavy; keep lean — ARP neighbors if possible
    neighbors = []
    try:
        r = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                parts = line.split()
                if len(parts) >= 2:
                    neighbors.append({"ip": parts[0], "mac": parts[1]})
        neighbors = neighbors[:40]
    except Exception:
        pass
    return _base("lan", local_ip=local_ip, arp_n=len(neighbors), arp_sample=neighbors[:12])


def ai_runtime() -> dict:
    """Ollama + OpenClaw + Pocket TTS reachability — no LLM call."""
    def _http(url: str, timeout: float = 2.0) -> dict:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return {"ok": True, "status": getattr(r, "status", 200), "bytes": len(r.read(2048))}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    ollama = _http("http://127.0.0.1:11434/api/tags")
    tags = []
    if ollama.get("ok"):
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
                tags = [m.get("name") for m in (json.loads(r.read().decode()).get("models") or []) if m.get("name")]
        except Exception:
            pass
    claw = _http("http://127.0.0.1:18789/")
    tts = _http("http://127.0.0.1:8000/health")
    if not tts.get("ok"):
        tts = _http("http://127.0.0.1:8000/")
    return _base(
        "ai_runtime",
        ollama=ollama,
        ollama_tags=tags,
        openclaw=claw,
        pocket_tts=tts,
        which={"qwen": shutil.which("qwen"), "openclaw": shutil.which("openclaw"), "ollama": shutil.which("ollama")},
    )


def volumes() -> dict:
    """Windows drives / mounts via psutil disk_partitions."""
    parts = []
    for p in psutil.disk_partitions(all=False):
        usage = None
        try:
            u = psutil.disk_usage(p.mountpoint)
            usage = {
                "total_gb": round(u.total / (1024**3), 2),
                "used_gb": round(u.used / (1024**3), 2),
                "free_gb": round(u.free / (1024**3), 2),
                "percent": u.percent,
            }
        except Exception as exc:
            usage = {"error": str(exc)}
        parts.append(
            {
                "device": p.device,
                "mount": p.mountpoint,
                "fstype": p.fstype,
                "opts": p.opts,
                "usage": usage,
            }
        )
    # flag removable-ish (Windows often leaves Removable in opts or thin free on D:)
    return _base("volumes", partitions=parts, n=len(parts))


def vision() -> dict:
    """Cam presence only — no capture here (cam:0 job owns stills)."""
    devices = []
    # lean: check if opencv can open 0 without keeping stream
    try:
        import cv2  # type: ignore

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        ok = bool(cap.isOpened())
        if ok:
            devices.append({"index": 0, "open": True})
        cap.release()
        return _base("vision", opencv=True, devices=devices, ok=ok or True)
    except Exception as exc:
        return _base("vision", opencv=False, devices=[], note=str(exc))
