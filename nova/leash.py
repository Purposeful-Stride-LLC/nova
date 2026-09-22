"""Thin leashes for external animals: OpenClaw (lobster) and Qwen Code (komodo).

NOVA does not swallow their processes. We probe status, stamp WHI facts, and
post mail to openclaw@local / qwen@local. OpenClaw may later act as messenger;
xAI/Ollama Brain adapter is a separate complete() seam in brain.py.
"""

from __future__ import annotations

import json
import shutil
import urllib.request
import hashlib
from pathlib import Path

from nova import breaklog, db, office

OPENCLAW_URL = "http://127.0.0.1:18789/"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"


def _http_ok(url: str, timeout: float = 3.0) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return {"ok": True, "status": getattr(r, "status", 200), "bytes": len(r.read(2048))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def openclaw_status() -> dict:
    office.ensure_workforce()
    http = _http_ok(OPENCLAW_URL)
    cli = shutil.which("openclaw")
    body = {
        "zulu": db.zulu(),
        "gateway_http": http,
        "cli": cli or "",
        "driver_hint": "ollama/qwen3.5:9b (fallback: llama3-groq-tool-use:8b)",
        "role": "messenger-candidate + coding agent",
    }
    whi = "Ax-CLAW" if http.get("ok") else "Tx-CLAW"
    db.put_fact(whi, "openclaw-status", json.dumps(body)[:4000])
    office.post_packet(
        dest="openclaw@local",
        mask="openclaw",
        whi=whi,
        kind="status",
        cite=OPENCLAW_URL,
        body=json.dumps(body)[:3500],
    )
    office.bump("openclaw@local", "jobs_run")

    if not http.get("ok"):
        breaklog.record(
            "openclaw-gateway",
            http.get("error") or "down",
            severity="warn",
            whi="Tx-CLAW",
            cite=OPENCLAW_URL,
            context=body,
        )
    return {"ok": bool(http.get("ok")), **body}


def qwen_status() -> dict:
    office.ensure_workforce()
    cli = shutil.which("qwen")
    settings = Path.home() / ".qwen" / "settings.json"
    model = ""
    base = ""
    if settings.is_file():
        try:
            cfg = json.loads(settings.read_text(encoding="utf-8"))
            model = ((cfg.get("model") or {}).get("name")) or ""
            prov = (cfg.get("modelProviders") or {}).get("openai") or []
            if prov:
                base = prov[0].get("baseUrl") or ""
        except Exception as exc:
            breaklog.record("qwen-settings", str(exc), severity="warn", whi="Tx-QWEN")
    ollama = _http_ok(OLLAMA_TAGS)
    tags: list[str] = []
    if ollama.get("ok"):
        try:
            with urllib.request.urlopen(OLLAMA_TAGS, timeout=3) as r:
                tags = [m.get("name") for m in (json.loads(r.read().decode()).get("models") or []) if m.get("name")]
        except Exception:
            pass
    has_code = any("codellama" in (t or "") for t in tags)
    body = {
        "zulu": db.zulu(),
        "cli": cli or "",
        "settings_model": model,
        "baseUrl": base,
        "ollama_up": bool(ollama.get("ok")),
        "codellama": has_code,
        "role": "komodo coder",
    }
    whi = "Ax-QWEN" if cli and ollama.get("ok") else "Tx-QWEN"
    db.put_fact(whi, "qwen-status", json.dumps(body)[:4000])
    office.post_packet(
        dest="qwen@local",
        mask="qwen",
        whi=whi,
        kind="status",
        cite=str(settings),
        body=json.dumps(body)[:3500],
    )
    office.bump("qwen@local", "jobs_run")
    if not cli or not ollama.get("ok"):
        breaklog.record(
            "qwen-leash",
            "cli missing or ollama down",
            severity="warn",
            whi="Tx-QWEN",
            context=body,
        )
    return {"ok": bool(cli) and bool(ollama.get("ok")), **body}


def handoff(dest: str, kind: str, body: str, whi: str = "Tx-HAND") -> int:
    """Steward/daemon mail to a leashed animal."""
    office.ensure_workforce()
    dest = dest if "@" in dest else f"{dest}@local"
    mask = dest.split("@")[0]
    return office.post_packet(
        dest=dest, mask=mask, whi=whi, kind=kind, cite="leash.handoff", body=body[:3500]
    )


def openclaw_run(
    message: str,
    *,
    session_id: str = "nova-mail",
    model: str = "ollama/qwen3.5:9b",
    timeout: int = 180,
    packet_id: int | None = None,
) -> dict:
    """Call real OpenClaw agent via CLI (gateway). Does not use Ollama mail mask.

    lobster llama3-groq-tool-use:8b overflows ~8k with full bootstrap; default
    model is qwen3.5:9b (32k). Writes reply into packet if packet_id set, and
    posts a return packet to brief@local on the same zulu clock.
    """
    import subprocess
    import tempfile

    office.ensure_workforce()
    cli = shutil.which("openclaw")
    if not cli:
        err = {"ok": False, "error": "openclaw cli missing", "zulu": db.zulu()}
        breaklog.record("openclaw-run", err["error"], severity="error", whi="Tx-CLAW")
        return err
    msg = (message or "").strip()
    if not msg:
        return {"ok": False, "error": "empty message", "zulu": db.zulu()}
    tmp = Path(tempfile.gettempdir()) / f"nova_claw_{db.zulu().replace(':', '')}.txt"
    tmp.write_text(msg[:4000], encoding="utf-8")
    cmd = [
        cli,
        "agent",
        "--session-id",
        session_id,
        "--model",
        model,
        "--message-file",
        str(tmp),
        "--json",
        "--timeout",
        str(timeout),
        "--thinking",
        "off",
    ]
    z0 = db.zulu()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout + 30)
        raw = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        data = {}
        try:
            # last JSON object in stdout
            start = raw.find("{")
            data = json.loads(raw[start:]) if start >= 0 else {}
        except Exception:
            data = {"parse_error": True, "raw": raw[:1500]}
        payloads = ((data.get("result") or {}).get("payloads")) or []
        text = ""
        if payloads:
            text = str(payloads[0].get("text") or "")
        ok = data.get("status") == "ok" or (proc.returncode == 0 and bool(text) and "Context overflow" not in text)
        if not ok and not text:
            text = raw[:1500] or f"exit {proc.returncode}"
        body = {
            "ok": bool(ok),
            "zulu": db.zulu(),
            "zulu_start": z0,
            "session_id": session_id,
            "model": model,
            "text": text[:3000],
            "runId": data.get("runId"),
            "status": data.get("status") or ("ok" if ok else "error"),
        }
        whi = "Ax-CLAW" if ok else "Tx-CLAW"
        db.put_fact(whi, "openclaw-run", json.dumps({k: body[k] for k in body if k != "text"})[:4000])
        if packet_id is not None:
            con = db.connect()
            row = con.execute("SELECT body FROM packets WHERE id=?", (packet_id,)).fetchone()
            prev = (row["body"] if row else "") or ""
            if "\n---\n" in prev:
                prev = prev.split("\n---\n", 1)[0]
            con.execute(
                "UPDATE packets SET status=?, body=? WHERE id=?",
                ("delivered" if ok else "fail", (prev + "\n---\n" + text)[:4000], packet_id),
            )
            con.commit()
            con.close()
        office.post_packet(
            dest="brief@local",
            mask="openclaw",
            whi=whi,
            kind="reply",
            cite=f"leash.openclaw_run:{session_id}",
            body=(text or json.dumps(body))[:3500],
        )
        office.bump("openclaw@local", "jobs_run")
        try:
            from nova import proof
            body["proof"] = proof.enforce_on_reply(text or "")
            if body["proof"].get("accepted") is False:
                body["ok"] = False
                body["status"] = "proof-reject"
        except Exception as _proof_exc:
            body["proof"] = {"ok": False, "error": str(_proof_exc)}
        if not ok:
            breaklog.record("openclaw-run", text[:500] or "failed", severity="warn", whi="Tx-CLAW", context=body)
        return body
    except Exception as exc:
        breaklog.record("openclaw-run", str(exc), severity="error", whi="Tx-CLAW")
        return {"ok": False, "error": str(exc), "zulu": db.zulu()}
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def qwen_run(prompt: str, *, cwd: str | None = None, timeout: int = 180) -> dict:
    """Komodo on leash — wrap hands.qwen.run_prompt (HIL before file writes)."""
    from nova.hands import qwen as qwen_hand
    return qwen_hand.run_prompt(prompt, cwd=cwd, timeout=timeout)


def proof_tree(paths: list[str] | tuple[str, ...] | None = None) -> dict:
    """Build PROOF bundle: relative tree lines + sha256 + bytes_total. No GPU."""
    root = Path(__file__).resolve().parents[1]
    paths = list(paths or [])
    tree: list[str] = []
    sha: dict[str, str] = {}
    total = 0
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = root / p
        if not p.is_file():
            tree.append(f"{raw}:MISSING")
            continue
        data = p.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        try:
            rel = str(p.relative_to(root))
        except Exception:
            rel = str(p)
        tree.append(f"{rel}:{len(data)}")
        sha[rel] = digest
        total += len(data)
    zulu = db.zulu() if hasattr(db, "zulu") else ""
    return {"ok": True, "tree": tree, "sha256": sha, "bytes_total": total, "zulu": zulu}
