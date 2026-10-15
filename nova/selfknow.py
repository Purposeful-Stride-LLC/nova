"""SELF block: generated self-knowledge for the system prompt AND the GUI panel (one source).

text() is the only renderer. Probes are read-only: DB opened mode=ro, sockets/HTTP on 127.0.0.1.
Pass probes=dict(...) (see gather()) to render deterministically in tests.
"""
from __future__ import annotations

import json
import re
import socket
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from nova.ctime import fmt

UNKNOWN = "unknown"
_PKG = Path(__file__).resolve().parent


def _home() -> Path:
    from nova import db
    return db.home()


def sched_job_keys() -> list[str]:
    """Job handlers the code knows (parsed from sched.py, not imported)."""
    try:
        src = (_PKG / "sched.py").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    keys = re.findall(r'key\s*==\s*"([^"]+)"', src) + re.findall(r'key\.startswith\("([^"]+)"', src)
    return sorted(set(keys))


def ro_connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)


def _db_probe(dbp: Path) -> dict:
    out: dict = {}
    try:
        con = ro_connect(dbp)
        try:
            rows = con.execute("SELECT id, name, enabled FROM jobs ORDER BY id").fetchall()
            out["jobs"] = [(r[1], int(r[2] or 0)) for r in rows]
            out["job_ids"] = {r[1]: int(r[0]) for r in rows}
            for t in ("facts", "observations", "chunks"):
                out[t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            out["reports_open"] = con.execute("SELECT count(*) FROM reports WHERE status='open'").fetchone()[0]
            out["packets_fail"] = con.execute("SELECT count(*) FROM packets WHERE status='fail'").fetchone()[0]
        finally:
            con.close()
    except Exception as exc:  # missing table/DB -> unknown
        out["db_error"] = str(exc)[:80]
    return out


def tts_up(port: int = 8000, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def ollama_loaded(timeout: float = 1.5) -> list[str] | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=timeout) as r:
            data = json.loads(r.read().decode())
        return [m.get("name", "?") for m in data.get("models") or []]
    except Exception:
        return None


def cam_last(home: Path) -> datetime | None:
    d = home / "data" / "artifacts" / "vision"
    try:
        newest = max((p.stat().st_mtime for p in d.glob("*.jpg")), default=None)
    except OSError:
        newest = None
    return datetime.fromtimestamp(newest, tz=timezone.utc) if newest else None


def gather() -> dict:
    home = _home()
    p = _db_probe(home / "data" / "NOVA.db")
    p["generated"] = datetime.now(timezone.utc)
    p["cam_last"] = cam_last(home)
    p["tts_up"] = tts_up()
    p["ollama"] = ollama_loaded()
    p["handlers"] = sched_job_keys()
    return p


def _n(v) -> str:
    return UNKNOWN if v is None else str(v)


KEY_JOBS = ("holmes", "cam:0", "thermal-check", "whistle", "nova-diary")


def text_v2(p: dict) -> str:
    """v2: compact (target 600-900 chars), state-specific voice line, job ids for proposals."""
    jobs = p.get("jobs")
    ids = p.get("job_ids") or {}
    if jobs is None:
        jobline = f"Jobs: {UNKNOWN} (job table unreadable)"
    else:
        on = [n for n, e in jobs if e]
        key = [n for n in KEY_JOBS if n in on] or on[:5]
        shown = ", ".join(f"{n} #{ids[n]}" if n in ids else n for n in key)
        more = len(on) - len(key)
        jobline = f"Jobs: {len(on)} enabled, daemon-run (queue is law): {shown}" + (f" +{more} more" if more > 0 else "")
    tts = p.get("tts_up")
    if tts is None:
        voice = "Voice: Pocket TTS :8000 state unknown; say text only."
    elif tts:
        voice = "Voice: Pocket TTS :8000 UP; I can speak aloud now (one short line, speak tag)."
    else:
        voice = "Voice: Pocket TTS :8000 DOWN; I cannot speak aloud now, text only."
    oll = p.get("ollama")
    oll_s = UNKNOWN if oll is None else (", ".join(oll) or "none loaded")
    cam_id = ids.get("cam:0")
    cmdline = ("Commands use numeric ids: /job off <id>, /job on <id>"
               + (f"; camera = /job off {cam_id}" if cam_id else ""))
    lines = [
        f"SELF (facts, generated {fmt(p.get('generated'))}):",
        "- NOVA fieldkit 2.1, local laptop (RTX 5050, 8 GB). Times in CT.",
        f"- Palace: SQLite RAG; {_n(p.get('facts'))} facts, {_n(p.get('observations'))} obs, {_n(p.get('chunks'))} chunks.",
        "- " + jobline + ".",
        f"- Vision: cam:0 photo every 15 min, features only. Last: {fmt(p.get('cam_last'))}.",
        "- " + voice,
        f"- Brain: local Ollama; loaded: {oll_s}.",
        f"- Mail: {_n(p.get('reports_open'))} reports open, {_n(p.get('packets_fail'))} packets failed; HIL approval.",
        "- " + cmdline + ".",
        "- Directives: queue is law; brief; observe, report, propose.",
        "LIMITS: chat cannot change jobs, write the DB, delete, browse or send. I propose the exact operator command; the operator runs it.",
        "UNKNOWN: not listed here or in palace hits = \"unknown - no record\".",
    ]
    return "\n".join(lines)


def text(probes: dict | None = None, version: int = 1) -> str:
    p = gather() if probes is None else probes
    if version >= 2:
        return text_v2(p)
    jobs = p.get("jobs")
    if jobs is None:
        jobline = f"Scheduler: {UNKNOWN} (job table unreadable)"
    else:
        on = [n for n, e in jobs if e]
        jobline = f"Scheduler (daemon-run, queue is law): {len(on)} enabled jobs: {', '.join(on)}"
    tts = p.get("tts_up")
    tts_s = UNKNOWN if tts is None else ("UP" if tts else "DOWN")
    oll = p.get("ollama")
    oll_s = UNKNOWN if oll is None else (", ".join(oll) or "none loaded")
    cam = p.get("cam_last")
    lines = [
        f"SELF (facts, generated {fmt(p.get('generated'))}):",
        "- I am NOVA fieldkit 2.1 on the operator's laptop (RTX 5050, 8 GB). I report times in CT.",
        f"- Palace: SQLite memory, {_n(p.get('facts'))} facts, {_n(p.get('observations'))} observations, {_n(p.get('chunks'))} chunks; RAG retrieval.",
        "- " + jobline + ".",
        f"- Vision: cam:0 still every 15 min (OpenCV features; no stored moondream text). Last still: {fmt(cam)}.",
        f"- Voice: Pocket TTS :8000 — {tts_s}. If DOWN I cannot speak aloud; text only.",
        f"- Brain: Ollama local; loaded now: {oll_s}.",
        f"- Mail room: packets/reports; {_n(p.get('reports_open'))} reports open, {_n(p.get('packets_fail'))} packets failed. HIL approval required.",
        "- Web: crawl/docs-scout jobs only, not from chat. Council masks give opinion only.",
        "LIMITS: From chat I cannot change jobs, write the DB, delete anything, or send mail/messages. I propose; the operator approves.",
        "UNKNOWN: if a fact or past action is not listed above, I say \"unknown\" and never invent it.",
    ]
    return "\n".join(lines)


def panel_text(probes: dict | None = None, version: int = 1) -> str:
    """GUI 'What NOVA knows about itself' panel: byte-identical to the injected block."""
    return text(probes, version)
