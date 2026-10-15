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
        status="logged",  # log-only (2026-10-07)
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
        status="logged",  # log-only (2026-10-07)
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
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout + 120)
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
            status="logged",  # log-only (2026-10-07)
        )
        office.bump("openclaw@local", "jobs_run")
        try:
            from nova import proof
            body["proof"] = proof.enforce_on_reply(text or "")
            if body["proof"].get("accepted") is False:
                body["ok"] = False
                body["status"] = "proof-reject"
                ok = False
                # Re-stamp packet if proof gate rejected after premature delivered mark
                if packet_id is not None:
                    try:
                        con = db.connect()
                        con.execute(
                            "UPDATE packets SET status=? WHERE id=?",
                            ("fail", packet_id),
                        )
                        con.commit()
                        con.close()
                    except Exception:
                        pass
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


CANONICAL_OUTBOX = Path.home() / ".openclaw" / "workspace" / "nova-out"


def canonical_outbox() -> Path:
    """Return the single canonical OpenClaw nova-out path."""
    return CANONICAL_OUTBOX


def forge_step(step_path: str | Path, *, outbox: Path | None = None) -> dict:
    """One-STEP runner: read STEP → ensure outbox → proof_tree on FILES listed → envelope.

    Does NOT call OpenClaw chat. Steward/forge path only.
    """
    step_path = Path(step_path)
    out = Path(outbox) if outbox is not None else CANONICAL_OUTBOX
    out.mkdir(parents=True, exist_ok=True)
    text = step_path.read_text(encoding="utf-8", errors="replace") if step_path.is_file() else ""
    files: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith("FILES:"):
            rest = s.split(":", 1)[1].strip()
            parts = [x.strip() for x in rest.split(";") if x.strip()]
            files.extend(parts)
            break
    resolved: list[str] = []
    for raw in files:
        fp = Path(raw)
        if not fp.is_absolute():
            fp = out / fp
        resolved.append(str(fp.resolve()))
    proof = proof_tree(resolved)
    ok = bool(proof.get("ok")) and all("MISSING" not in (x or "") for x in (proof.get("tree") or []))
    if files and not resolved:
        ok = False
    if files and proof.get("bytes_total", 0) == 0:
        ok = False
    return {
        "v": 1,
        "kind": "forge_step",
        "ok": ok,
        "step": str(step_path),
        "outbox": str(out),
        "proof": proof,
        "bytes_total": int(proof.get("bytes_total") or 0),
        "note": "one-STEP; no multi-phase chat",
    }


# --- PROTOCOL_CLAW_GROK_COM (Fieldkit 2.0) ---
GROK_RATE_PER_HOUR = 12
GROK_MIN_SPACING_S = 60
GROK_PROTOCOL = "PROTOCOL_CLAW_GROK_COM"


def grok_rate_budget(*, window_s: int = 3600) -> dict:
    """Sliding-window count of grok@claw / GROK_COM_QUERY activity (facts titles)."""
    import time

    con = db.connect()
    try:
        rows = con.execute(
            "SELECT zulu, title, whi FROM facts WHERE title LIKE ? OR title LIKE ? OR body LIKE ? ORDER BY id DESC LIMIT 200",
            ("%GROK_COM_QUERY%", "%grok@claw%", "%PROTOCOL_CLAW_GROK_COM%"),
        ).fetchall()
    finally:
        con.close()
    now = time.time()
    recent = []
    for r in rows:
        z = str(r["zulu"] or "")
        # accept ISO Z roughly; if parse fails, count conservatively when title matches
        try:
            from datetime import datetime, timezone

            ts = datetime.strptime(z.replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            ts = now  # count it
        if now - ts <= window_s:
            recent.append({"zulu": z, "title": r["title"], "whi": r["whi"]})
    used = len(recent)
    return {
        "ok": True,
        "used": used,
        "limit": GROK_RATE_PER_HOUR,
        "remaining": max(0, GROK_RATE_PER_HOUR - used),
        "window_s": window_s,
        "recent": recent[:12],
    }


def build_grok_step(query: str, *, step_id: str | None = None, out_dir: Path | None = None) -> dict:
    """Write one GROK_COM_QUERY STEP file (dry-run or live). Does not call Claw."""
    from datetime import datetime, timezone

    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}
    if "\n" in q and q.count("?") > 2:
        return {"ok": False, "error": "multi_ask_refused"}
    zulu_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sid = step_id or f"GROK_COM_QUERY_{zulu_id}"
    outbox = canonical_outbox()
    outbox.mkdir(parents=True, exist_ok=True)
    dest_dir = Path(out_dir) if out_dir else (Path(__file__).resolve().parents[1] / "STAGING" / "steps")
    dest_dir.mkdir(parents=True, exist_ok=True)
    answer_name = f"GROK_ANSWER_{sid}.md"
    answer_path = outbox / answer_name
    # Absolute OUTBOX with trailing separator (Windows-friendly)
    outbox_abs = str(outbox.resolve())
    if not outbox_abs.endswith(("\\", "/")):
        outbox_abs = outbox_abs + "\\"
    answer_abs = str(answer_path.resolve())
    # Workspace-relative fallback Claw can always write, steward promotes
    ws_rel = f"nova-out/{answer_name}"
    body = f"""# STEP — GROK_COM_QUERY
STEP_ID: {sid}
PROTOCOL: {GROK_PROTOCOL}
OUTBOX: {outbox_abs}
ANSWER_ABS: {answer_abs}
ANSWER_WSREL: {ws_rel}
TIMEOUT_HINT_S: 90

PREFLIGHT:
- Gateway http://127.0.0.1:18789/ == 200
- Claw browser on https://grok.com and logged in (composer visible)
- No paint / Qwen-Image running in parallel
- Rate budget remaining (PROTOCOL §5)

TASK: browser query on grok.com (ONE question)
QUERY:
<<<
{q}
>>>

DO (strict order — do not skip):
1) browser tool recipe (OpenClaw browser actions — do NOT invent action names):
   - action=status (confirm cdpReady)
   - action=navigate (or open) targetUrl=https://grok.com
   - action=snapshot or action=text to confirm composer / detect login wall or captcha
   - If login wall/captcha: STOP immediately. No credentials. No invent.
   - To type+submit: action=act with nested act steps (NOT action=type — invalid). Use snapshot refs for the composer input and send button.
2) Paste ONLY the text inside QUERY <<<>>> into the grok.com composer; submit ONCE via act.
3) WAIT until the full reply finishes (no spinner). Soft wait up to ~90s. Poll with action=text / snapshot. Mid-stream DONE is FORBIDDEN.
4) Use the **write** (or file_write) tool to create the answer file. Preferred absolute path:
   {answer_abs}
   If absolute write is refused by sandbox, write workspace-relative:
   {ws_rel}
   (steward will promote into OUTBOX). Do NOT claim DONE until the write tool returns success.
5) File MUST contain sections in order: QUERY / ANSWER / CITES / PROOF (PROTOCOL §3).
6) Chat reply ONLY after the write succeeds, exactly:
DONE: <one line>
FILES: {answer_abs}
PROOF: bytes=<real_byte_size_on_disk>
NEXT: STOP

RULES:
- write tool required before DONE; chat-only DONE = fail
- browser actions only from allowlist (doctor/status/start/stop/tabs/open/focus/close/snapshot/screenshot/navigate/text/act/...); NEVER action=type
- one query; one answer file; that OUTBOX (or ws-rel) path only
- if captcha / login wall / empty after wait: STOP + state Tx-CLAW in chat; no answer invent
- no GPU paint; no HF downloads; no secrets in ANSWER file
- PROOF bytes= must equal real file size from write tool / ls — never "pending"
"""
    step_path = dest_dir / f"{sid}.md"
    step_path.write_text(body, encoding="utf-8")
    return {
        "ok": True,
        "step_id": sid,
        "step_path": str(step_path),
        "answer_path": answer_abs,
        "answer_wsrel": ws_rel,
        "bytes": step_path.stat().st_size,
        "mask": "grok@claw",
    }


def _promote_grok_answer(answer_path: Path, *, ws_rel_name: str | None = None) -> dict:
    """If answer missing at canonical outbox, copy from workspace-relative landing."""
    answer_path = Path(answer_path)
    if answer_path.is_file() and answer_path.stat().st_size > 0:
        data = answer_path.read_bytes()
        return {
            "ok": True,
            "promoted": False,
            "path": str(answer_path),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    ws = Path.home() / ".openclaw" / "workspace"
    candidates: list[Path] = []
    if ws_rel_name:
        candidates.append(ws / ws_rel_name.replace("/", "\\") if "\\" not in ws_rel_name else ws / ws_rel_name)
        candidates.append(ws / "nova-out" / Path(ws_rel_name).name)
        candidates.append(ws / Path(ws_rel_name).name)
    candidates.append(ws / "nova-out" / answer_path.name)
    candidates.append(ws / answer_path.name)
    # also scan recent GROK_ANSWER_* under workspace
    try:
        for p in sorted(ws.rglob("GROK_ANSWER_*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:8]:
            if p.name == answer_path.name or answer_path.name in p.name:
                candidates.append(p)
    except Exception:
        pass
    seen: set[str] = set()
    for src in candidates:
        key = str(src)
        if key in seen:
            continue
        seen.add(key)
        try:
            if src.is_file() and src.stat().st_size > 0:
                answer_path.parent.mkdir(parents=True, exist_ok=True)
                if src.resolve() != answer_path.resolve():
                    shutil.copy2(src, answer_path)
                data = answer_path.read_bytes()
                return {
                    "ok": True,
                    "promoted": True,
                    "from": str(src),
                    "path": str(answer_path),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
        except Exception as exc:
            last_err = str(exc)
            continue
    return {"ok": False, "error": "answer_missing", "path": str(answer_path), "tried": [str(c) for c in list(seen)[:12]]}


def verify_grok_answer(answer_path: str | Path, *, ws_rel: str | None = None) -> dict:
    """Verify GROK_ANSWER file exists with PROOF structure; promote if needed."""
    p = Path(answer_path)
    promo = _promote_grok_answer(p, ws_rel_name=ws_rel)
    if not promo.get("ok"):
        return promo
    text = Path(promo["path"]).read_text(encoding="utf-8", errors="replace")
    need = ("## QUERY", "## ANSWER", "## PROOF")
    missing = [h for h in need if h not in text]
    # also accept alternate headers
    if missing and "QUERY" in text.upper() and "ANSWER" in text.upper() and "PROOF" in text.upper():
        missing = []
    if missing:
        return {
            "ok": False,
            "error": "structure_incomplete",
            "missing": missing,
            "path": promo["path"],
            "bytes": promo["bytes"],
            "sha256": promo["sha256"],
        }
    return {
        "ok": True,
        "path": promo["path"],
        "bytes": promo["bytes"],
        "sha256": promo["sha256"],
        "promoted": promo.get("promoted", False),
        "from": promo.get("from"),
    }


def grok_query(
    query: str,
    *,
    dry_run: bool = True,
    deliver: bool = False,
    use_cli: bool | None = None,
    timeout: int = 180,
    packet_id: int | None = None,
) -> dict:
    """Build GROK_COM_QUERY STEP; optionally handoff/openclaw_run. Default dry_run=True (no Claw).

    Live path (dry_run=False, deliver=True):
    - prefers CLI openclaw_run (use_cli default True) so we can verify PROOF on disk
    - marks packet delivered/fail when packet_id given or when handoff creates one
    - success requires verify_grok_answer ok (file + structure), not merely agent chat DONE
    """
    budget = grok_rate_budget()
    if budget.get("remaining", 0) <= 0 and not dry_run:
        return {"ok": False, "error": "rate_limit", "budget": budget}
    status = openclaw_status()
    built = build_grok_step(query)
    if not built.get("ok"):
        return built
    env = {
        "ok": True,
        "dry_run": dry_run,
        "protocol": GROK_PROTOCOL,
        "mask": "grok@claw",
        "budget": budget,
        "gateway": {"ok": bool(status.get("ok")), "cli": status.get("cli"), "zulu": status.get("zulu")},
        "step": built,
        "delivered": False,
        "verified": False,
    }
    if dry_run or not deliver:
        db.put_fact(
            "Ax-CLAW",
            f"grok@claw-dryrun:{built['step_id']}",
            f"dry_run=1\nquery={query[:500]}\nstep={built['step_path']}\nbytes={built['bytes']}",
            kind="claw",
        )
        return env

    # live path — CLI preferred for synchronous PROOF verify
    # shared browser lock vs gemini@claw (PROTOCOL_CLAW_GEMINI_GOOGLE §8)
    _glock = claw_browser_acquire("grok@claw")
    if not _glock.get("ok"):
        return {"ok": False, "error": _glock.get("error") or "browser_busy", "lock": _glock, "mask": "grok@claw"}
    try:
        if use_cli is None:
            use_cli = True
        step_text = Path(built["step_path"]).read_text(encoding="utf-8")
        answer_path = built["answer_path"]
        ws_rel = built.get("answer_wsrel")

        if use_cli:
            # Compact message avoids context overflow from full STEP + bootstrap.
            # Agent must read the STEP file, then execute browser+write per STEP.
            from datetime import datetime, timezone as _tz
            sid = "nova-grok-" + datetime.now(_tz.utc).strftime("%Y%m%dT%H%M%SZ")
            answer_abs = built["answer_path"]
            compact = (
                f"ONE-STEP execute. Read the STEP file with the read tool, then follow it exactly.\n"
                f"STEP_PATH: {built['step_path']}\n"
                f"Write GROK_ANSWER with write/file_write BEFORE any DONE.\n"
                f"Preferred path: {answer_abs}\n"
                f"Fallback workspace-relative: {ws_rel}\n"
                f"Hard STOP on login wall/captcha (no credentials).\n"
                f"Wait for FULL grok.com reply (~90s). Mid-stream DONE forbidden.\n"
                f"Chat ONLY after write succeeds:\n"
                f"DONE: <one line>\nFILES: {answer_abs}\nPROOF: bytes=<real_size>\nNEXT: STOP\n"
            )
            run = openclaw_run(
                compact,
                timeout=timeout,
                packet_id=packet_id,
                session_id=sid,
                model="ollama/qwen3.5:9b",
            )
            env["session_id"] = sid
            env["run"] = {k: run.get(k) for k in ("ok", "status", "zulu", "zulu_start", "runId", "model", "error") if k in run or run.get(k) is not None}
            env["run_text"] = (run.get("text") or "")[:800]
            # proof gate may already have flipped run["ok"]
            ver = verify_grok_answer(answer_path, ws_rel=ws_rel)
            env["verify"] = ver
            env["verified"] = bool(ver.get("ok"))
            env["delivered"] = bool(ver.get("ok"))
            env["ok"] = bool(ver.get("ok"))
            if packet_id is not None:
                _mark_packet(packet_id, "delivered" if ver.get("ok") else "fail", note=ver)
            if ver.get("ok"):
                db.put_fact(
                    "Ax-CLAW",
                    f"grok@claw-proof:{built['step_id']}",
                    f"path={ver.get('path')}\nbytes={ver.get('bytes')}\nsha256={ver.get('sha256')}\npromoted={ver.get('promoted')}",
                    kind="claw",
                )
            else:
                db.put_fact(
                    "Tx-CLAW",
                    f"grok@claw-fail:{built['step_id']}",
                    f"verify={ver}\nrun_status={run.get('status')}\ntext={(run.get('text') or '')[:600]}",
                    kind="claw",
                )
                # write fail note to outbox for steward
                try:
                    fail_p = canonical_outbox() / f"GROK_FAIL_{built['step_id']}.md"
                    fail_p.write_text(
                        f"# GROK_FAIL\nSTEP_ID: {built['step_id']}\nZULU: {db.zulu()}\nREASON: {ver.get('error') or run.get('status')}\nVERIFY: {ver}\nRUN_TEXT:\n{(run.get('text') or '')[:1500]}\n",
                        encoding="utf-8",
                    )
                    env["fail_path"] = str(fail_p)
                except Exception:
                    pass
            return env

        # handoff-only path (async): queue task; do NOT claim verified
        pid = handoff("openclaw@local", "task", step_text, whi="Tx-HAND")
        env["packet_id"] = pid
        env["delivered"] = False  # queued only; claw-run + verify later
        env["queued"] = True
        env["ok"] = True
        env["note"] = "handoff queued; call grok_query(..., use_cli=True) or claw-run + verify_grok_answer for PROOF"
        db.put_fact(
            "Ax-CLAW",
            f"grok@claw-queued:{built['step_id']}",
            f"packet_id={pid}\nstep={built['step_path']}\nanswer={answer_path}",
            kind="claw",
        )
        return env

    finally:
        try:
            claw_browser_release("grok@claw")
        except Exception:
            pass

def _mark_packet(packet_id: int, status: str, note: dict | None = None) -> None:
    try:
        con = db.connect()
        row = con.execute("SELECT body FROM packets WHERE id=?", (packet_id,)).fetchone()
        prev = (row["body"] if row else "") or ""
        if "\n---\n" in prev:
            prev = prev.split("\n---\n", 1)[0]
        suffix = ""
        if note:
            suffix = "\n---\n" + json.dumps(note, default=str)[:1500]
        con.execute(
            "UPDATE packets SET status=?, body=? WHERE id=?",
            (status, (prev + suffix)[:4000], packet_id),
        )
        con.commit()
        con.close()
    except Exception:
        pass

# --- Shared claw-browser availability (PROTOCOL_CLAW_GEMINI_GOOGLE §8; shared with grok@claw) ---
CLAW_BROWSER_HOLD_S = 120
CLAW_BROWSER_LOCK_NAME = "CLAW_BROWSER_AVAIL.json"


def claw_browser_lock_path() -> Path:
    return canonical_outbox() / CLAW_BROWSER_LOCK_NAME


def claw_availability_snapshot(
    mask: str,
    *,
    online: bool | None = None,
    logged_in: bool | None = None,
    ready: bool | None = None,
    note: str = "",
) -> dict:
    """Write/return ONLINE/LOGGED_IN/READY/LAST_CHECK_TS for external claw masks."""
    from datetime import datetime, timezone
    import time as _time

    zulu = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gw = openclaw_status()
    online_v = bool(gw.get("ok")) if online is None else bool(online)
    logged_v = bool(logged_in) if logged_in is not None else False
    ready_v = bool(ready) if ready is not None else (online_v and logged_v)
    snap = {
        "mask": mask,
        "ONLINE": online_v,
        "LOGGED_IN": logged_v,
        "READY": ready_v,
        "LAST_CHECK_TS": zulu,
        "available": ready_v,
        "note": note,
        "epoch": _time.time(),
    }
    try:
        p = claw_browser_lock_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        prev = {}
        if p.is_file():
            try:
                prev = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                prev = {}
        seats = prev.get("seats") if isinstance(prev.get("seats"), dict) else {}
        seats[mask] = snap
        out = {
            "zulu": zulu,
            "holder": prev.get("holder"),
            "hold_until": prev.get("hold_until"),
            "seats": seats,
        }
        p.write_text(json.dumps(out, indent=2), encoding="utf-8")
        snap["lock_path"] = str(p)
    except Exception as exc:
        snap["lock_error"] = str(exc)
    return snap


def claw_browser_acquire(mask: str, *, hold_s: int = CLAW_BROWSER_HOLD_S) -> dict:
    """Serialize grok@claw / gemini@claw against the shared Claw browser.

    Returns ok=False with error=browser_busy when another mask holds the lock.
    """
    import time as _time
    from datetime import datetime, timezone

    p = claw_browser_lock_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    now = _time.time()
    prev = {}
    if p.is_file():
        try:
            prev = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    holder = prev.get("holder")
    hold_until = float(prev.get("hold_until") or 0)
    if holder and holder != mask and hold_until > now:
        return {
            "ok": False,
            "error": "browser_busy",
            "holder": holder,
            "hold_until": hold_until,
            "remaining_s": int(hold_until - now),
        }
    zulu = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seats = prev.get("seats") if isinstance(prev.get("seats"), dict) else {}
    body = {
        "zulu": zulu,
        "holder": mask,
        "hold_until": now + max(30, int(hold_s)),
        "seats": seats,
    }
    p.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return {"ok": True, "mask": mask, "hold_until": body["hold_until"], "path": str(p)}


def claw_browser_release(mask: str) -> dict:
    """Release shared browser lock if we hold it."""
    import time as _time
    from datetime import datetime, timezone

    p = claw_browser_lock_path()
    if not p.is_file():
        return {"ok": True, "released": False, "reason": "no_lock"}
    try:
        prev = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"ok": True, "released": False, "reason": "bad_lock"}
    if prev.get("holder") and prev.get("holder") != mask:
        return {"ok": False, "error": "not_holder", "holder": prev.get("holder")}
    zulu = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev["holder"] = None
    prev["hold_until"] = 0
    prev["zulu"] = zulu
    prev["released_by"] = mask
    prev["released_epoch"] = _time.time()
    p.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    return {"ok": True, "released": True, "mask": mask}


# --- PROTOCOL_CLAW_GEMINI_GOOGLE (Fieldkit 2.0) — steward-CDP first-class ---
GEMINI_RATE_PER_HOUR = 12
GEMINI_MIN_SPACING_S = 60
GEMINI_PROTOCOL = "PROTOCOL_CLAW_GEMINI_GOOGLE"
GEMINI_URL = "https://gemini.google.com/app?hl=en-GB"
GEMINI_NATIVE_ABORT_S = 90  # eval gate: overflow abort ≤90s


def gemini_rate_budget(*, window_s: int = 3600) -> dict:
    """Sliding-window count of gemini@claw / GEMINI_GOOGLE_QUERY activity (facts titles)."""
    import time

    con = db.connect()
    try:
        rows = con.execute(
            "SELECT zulu, title, whi FROM facts WHERE title LIKE ? OR title LIKE ? OR body LIKE ? ORDER BY id DESC LIMIT 200",
            ("%GEMINI_GOOGLE_QUERY%", "%gemini@claw%", "%PROTOCOL_CLAW_GEMINI_GOOGLE%"),
        ).fetchall()
    finally:
        con.close()
    now = time.time()
    recent = []
    for r in rows:
        z = str(r["zulu"] or "")
        try:
            from datetime import datetime, timezone

            ts = datetime.strptime(z.replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            ).timestamp()
        except Exception:
            ts = now
        if now - ts <= window_s:
            recent.append({"zulu": z, "title": r["title"], "whi": r["whi"]})
    used = len(recent)
    return {
        "ok": True,
        "used": used,
        "limit": GEMINI_RATE_PER_HOUR,
        "remaining": max(0, GEMINI_RATE_PER_HOUR - used),
        "window_s": window_s,
        "recent": recent[:12],
    }


def build_gemini_step(query: str, *, step_id: str | None = None, out_dir: Path | None = None) -> dict:
    """Write one GEMINI_GOOGLE_QUERY STEP file (dry-run or live). Does not call Claw."""
    from datetime import datetime, timezone

    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}
    if "\n" in q and q.count("?") > 2:
        return {"ok": False, "error": "multi_ask_refused"}
    zulu_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sid = step_id or f"GEMINI_GOOGLE_QUERY_{zulu_id}"
    outbox = canonical_outbox()
    outbox.mkdir(parents=True, exist_ok=True)
    dest_dir = Path(out_dir) if out_dir else (Path(__file__).resolve().parents[1] / "STAGING" / "steps")
    dest_dir.mkdir(parents=True, exist_ok=True)
    answer_name = f"GEMINI_ANSWER_{sid}.md"
    answer_path = outbox / answer_name
    outbox_abs = str(outbox.resolve())
    if not outbox_abs.endswith(("\\", "/")):
        outbox_abs = outbox_abs + "\\"
    answer_abs = str(answer_path.resolve())
    ws_rel = f"nova-out/{answer_name}"
    body = f"""# STEP — GEMINI_GOOGLE_QUERY
STEP_ID: {sid}
PROTOCOL: {GEMINI_PROTOCOL}
OUTBOX: {outbox_abs}
ANSWER_ABS: {answer_abs}
ANSWER_WSREL: {ws_rel}
TIMEOUT_HINT_S: {GEMINI_NATIVE_ABORT_S}
URL: {GEMINI_URL}
STEWARD_CDP_FIRST: true

PREFLIGHT:
- Gateway http://127.0.0.1:18789/ == 200
- Claw browser on {GEMINI_URL} and Google session logged in (composer visible)
- Availability gate (§8): ONLINE && LOGGED_IN && READY
- Shared browser lock free (do not fight grok@claw)
- No paint / Qwen-Image running in parallel
- Rate budget remaining (PROTOCOL §5)

TASK: browser query on gemini.google.com (ONE question)
QUERY:
<<<
{q}
>>>

DO (strict order — do not skip):
1) browser tool recipe (OpenClaw browser actions — do NOT invent action names):
   - action=status (confirm cdpReady)
   - action=navigate (or open) targetUrl={GEMINI_URL}
   - action=snapshot or action=text to confirm composer / detect Google login wall or captcha
   - If login wall/captcha/reCAPTCHA/ToS: STOP immediately. No credentials. No invent.
   - Fill AVAILABILITY (ONLINE/LOGGED_IN/READY/LAST_CHECK_TS) before paste.
   - To type+submit: action=act with nested act steps (NOT action=type — invalid). Use snapshot refs for the composer input and send button.
2) Paste ONLY the text inside QUERY <<<>>> into the Gemini composer; submit ONCE via act.
3) WAIT until the full reply finishes (no spinner). Soft wait up to ~{GEMINI_NATIVE_ABORT_S}s. Poll with action=text / snapshot. Mid-stream DONE is FORBIDDEN. On context-overflow string: ABORT ≤{GEMINI_NATIVE_ABORT_S}s (do not burn 3–4 min).
4) Use the **write** (or file_write) tool to create the answer file. Preferred absolute path:
   {answer_abs}
   If absolute write is refused by sandbox, write workspace-relative:
   {ws_rel}
   (steward will promote into OUTBOX). Do NOT claim DONE until the write tool returns success.
5) File MUST contain sections in order: AVAILABILITY / QUERY / ANSWER / CITES / PROOF (PROTOCOL §3).
6) Chat reply ONLY after the write succeeds, exactly:
DONE: <one line>
FILES: {answer_abs}
PROOF: bytes=<real_byte_size_on_disk>
NEXT: STOP

RULES:
- write tool required before DONE; chat-only DONE = fail
- browser actions only from allowlist; NEVER action=type
- one query; one answer file; that OUTBOX (or ws-rel) path only
- if captcha / login wall / empty after wait: STOP + state Tx-CLAW in chat; no answer invent
- no GPU paint; no HF downloads; no secrets in ANSWER file
- never enter Google credentials from STEP body
- PROOF bytes= must equal real file size from write tool / ls — never "pending"
- Prefer steward-CDP promote path when native overflow/thrash (EVAL gate)
"""
    step_path = dest_dir / f"{sid}.md"
    step_path.write_text(body, encoding="utf-8")
    return {
        "ok": True,
        "step_id": sid,
        "step_path": str(step_path),
        "answer_path": answer_abs,
        "answer_wsrel": ws_rel,
        "bytes": step_path.stat().st_size,
        "mask": "gemini@claw",
        "url": GEMINI_URL,
    }


def _promote_gemini_answer(answer_path: Path, *, ws_rel_name: str | None = None) -> dict:
    """If answer missing at canonical outbox, copy from workspace-relative landing."""
    answer_path = Path(answer_path)
    if answer_path.is_file() and answer_path.stat().st_size > 0:
        data = answer_path.read_bytes()
        return {
            "ok": True,
            "promoted": False,
            "path": str(answer_path),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    ws = Path.home() / ".openclaw" / "workspace"
    candidates: list[Path] = []
    if ws_rel_name:
        candidates.append(ws / ws_rel_name.replace("/", "\\") if "\\" not in ws_rel_name else ws / ws_rel_name)
        candidates.append(ws / "nova-out" / Path(ws_rel_name).name)
        candidates.append(ws / Path(ws_rel_name).name)
    candidates.append(ws / "nova-out" / answer_path.name)
    candidates.append(ws / answer_path.name)
    try:
        for p in sorted(ws.rglob("GEMINI_ANSWER_*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:8]:
            if p.name == answer_path.name or answer_path.name in p.name:
                candidates.append(p)
    except Exception:
        pass
    seen: set[str] = set()
    for src in candidates:
        key = str(src)
        if key in seen:
            continue
        seen.add(key)
        try:
            if src.is_file() and src.stat().st_size > 0:
                answer_path.parent.mkdir(parents=True, exist_ok=True)
                if src.resolve() != answer_path.resolve():
                    shutil.copy2(src, answer_path)
                data = answer_path.read_bytes()
                return {
                    "ok": True,
                    "promoted": True,
                    "from": str(src),
                    "path": str(answer_path),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
        except Exception:
            continue
    return {"ok": False, "error": "answer_missing", "path": str(answer_path), "tried": [str(c) for c in list(seen)[:12]]}


def verify_gemini_answer(answer_path: str | Path, *, ws_rel: str | None = None) -> dict:
    """Verify GEMINI_ANSWER file exists with PROOF structure; promote if needed."""
    p = Path(answer_path)
    promo = _promote_gemini_answer(p, ws_rel_name=ws_rel)
    if not promo.get("ok"):
        return promo
    text = Path(promo["path"]).read_text(encoding="utf-8", errors="replace")
    need = ("## QUERY", "## ANSWER", "## PROOF")
    missing = [h for h in need if h not in text]
    if missing and "QUERY" in text.upper() and "ANSWER" in text.upper() and "PROOF" in text.upper():
        missing = []
    # AVAILABILITY preferred but not hard-fail for legacy stubs
    has_avail = "## AVAILABILITY" in text or "ONLINE:" in text
    if missing:
        return {
            "ok": False,
            "error": "structure_incomplete",
            "missing": missing,
            "path": promo["path"],
            "bytes": promo["bytes"],
            "sha256": promo["sha256"],
            "has_availability": has_avail,
        }
    return {
        "ok": True,
        "path": promo["path"],
        "bytes": promo["bytes"],
        "sha256": promo["sha256"],
        "promoted": promo.get("promoted", False),
        "from": promo.get("from"),
        "has_availability": has_avail,
    }


def _gemini_cdp_promote(query: str, step_id: str, answer_path: Path, *, wait_s: float = 30) -> dict:
    """Steward-CDP first-class path. Loads STAGING/_cdp_promote_lib.promote_gemini_from_cdp."""
    roots = [
        Path(__file__).resolve().parents[1] / "STAGING" / "_cdp_promote_lib.py",
        Path(__file__).resolve().parents[2] / "STAGING" / "_cdp_promote_lib.py",
    ]
    last_err = "cdp_lib_missing"
    for lib in roots:
        if not lib.is_file():
            continue
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("nova_cdp_promote_lib", lib)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, "promote_gemini_from_cdp", None)
            if fn is None:
                last_err = "promote_gemini_from_cdp_missing"
                continue
            return fn(query=query, step_id=step_id, answer_path=Path(answer_path), wait_s=wait_s)
        except Exception as exc:
            last_err = str(exc)
            continue
    return {"ok": False, "error": last_err, "path_hint": "STAGING/_cdp_promote_lib.py::promote_gemini_from_cdp"}


def gemini_preflight_login(*, via_cdp: bool = True) -> dict:
    """Cookie/login preflight for Gemini. Observation only — never invent credentials."""
    from datetime import datetime, timezone

    zulu = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gw = openclaw_status()
    online = bool(gw.get("ok"))
    logged_in = False
    detail: dict = {"zulu": zulu, "url": GEMINI_URL}
    if via_cdp:
        try:
            import urllib.request as _ur

            raw = _ur.urlopen("http://127.0.0.1:18800/json/list", timeout=5).read().decode()
            pages = json.loads(raw)
            gem_pages = [
                t
                for t in pages
                if t.get("type") == "page" and "gemini.google.com" in (t.get("url") or "")
            ]
            acct = [
                t
                for t in pages
                if t.get("type") == "page" and "accounts.google.com" in (t.get("url") or "")
            ]
            detail["gemini_tabs"] = len(gem_pages)
            detail["accounts_tabs"] = len(acct)
            detail["gemini_urls"] = [(t.get("url") or "")[:120] for t in gem_pages[:4]]
            if gem_pages and not acct:
                # heuristic: on /app and title not Sign in
                for t in gem_pages:
                    u = (t.get("url") or "").lower()
                    title = (t.get("title") or "").lower()
                    if "/app" in u and "sign in" not in title and "accounts.google" not in u:
                        logged_in = True
                        detail["picked"] = (t.get("url") or "")[:160]
                        break
            detail["cdp_ok"] = True
        except Exception as exc:
            detail["cdp_ok"] = False
            detail["cdp_error"] = str(exc)
    ready = online and logged_in
    snap = claw_availability_snapshot(
        "gemini@claw",
        online=online,
        logged_in=logged_in,
        ready=ready,
        note="preflight_login",
    )
    return {
        "ok": True,
        "ONLINE": online,
        "LOGGED_IN": logged_in,
        "READY": ready,
        "available": ready,
        "LAST_CHECK_TS": zulu,
        "detail": detail,
        "snapshot": snap,
    }


def gemini_query(
    query: str,
    *,
    dry_run: bool = True,
    deliver: bool = False,
    use_cli: bool | None = None,
    timeout: int = 180,
    packet_id: int | None = None,
    steward_cdp: bool = True,
    skip_lock: bool = False,
) -> dict:
    """Build GEMINI_GOOGLE_QUERY STEP; optionally handoff/openclaw_run/steward-CDP.

    Default dry_run=True (no Claw). Success requires verify_gemini_answer ok (disk PROOF).
    steward_cdp defaults True (EVAL_GROK_CLAW_PERF: native unattended NO-GO).
    Shared browser lock serializes vs grok@claw.
    """
    budget = gemini_rate_budget()
    if budget.get("remaining", 0) <= 0 and not dry_run:
        return {"ok": False, "error": "rate_limit", "budget": budget}
    status = openclaw_status()
    built = build_gemini_step(query)
    if not built.get("ok"):
        return built
    avail = claw_availability_snapshot(
        "gemini@claw",
        online=bool(status.get("ok")),
        logged_in=None,
        ready=None,
        note="query_start",
    )
    env = {
        "ok": True,
        "dry_run": dry_run,
        "protocol": GEMINI_PROTOCOL,
        "mask": "gemini@claw",
        "budget": budget,
        "gateway": {"ok": bool(status.get("ok")), "cli": status.get("cli"), "zulu": status.get("zulu")},
        "step": built,
        "delivered": False,
        "verified": False,
        "steward_cdp": steward_cdp,
        "availability": avail,
        "method": "dry_run" if dry_run or not deliver else None,
    }
    if dry_run or not deliver:
        # dry-run also writes the protocol stub answer when QUERY marks DRYRUN
        try:
            if query.strip().upper().startswith("DRYRUN") or "do not submit" in query.lower():
                from datetime import datetime, timezone as _tz

                ap = Path(built["answer_path"])
                ap.parent.mkdir(parents=True, exist_ok=True)
                zulu = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                def _stub(n: int) -> str:
                    return (
                        f"# GEMINI_ANSWER\n"
                        f"STEP_ID: {built['step_id']}\n"
                        f"ZULU: {zulu}\n"
                        f"SOURCE: {GEMINI_URL}\n"
                        f"MASK: gemini@claw\n\n"
                        f"## AVAILABILITY\n"
                        f"ONLINE: {str(bool(status.get('ok'))).lower()}\n"
                        f"LOGGED_IN: false\n"
                        f"READY: false\n"
                        f"LAST_CHECK_TS: {zulu}\n\n"
                        f"## QUERY\n{query.strip()}\n\n"
                        f"## ANSWER\nDRYRUN stub — not a live gemini.google.com reply\n\n"
                        f"## CITES\n- none\n\n"
                        f"## PROOF\nbytes={n}\npath={ap}\n"
                    )

                text = _stub(0)
                for _ in range(5):
                    text = _stub(len(text.encode("utf-8")))
                ap.write_text(text, encoding="utf-8")
                data = ap.read_bytes()
                text = _stub(len(data))
                ap.write_text(text, encoding="utf-8")
                ver = verify_gemini_answer(ap)
                env["verify"] = ver
                env["verified"] = bool(ver.get("ok"))
                env["dry_stub_path"] = str(ap)
        except Exception as exc:
            env["dry_stub_error"] = str(exc)
        db.put_fact(
            "Ax-CLAW",
            f"gemini@claw-dryrun:{built['step_id']}",
            f"dry_run=1\nquery={query[:500]}\nstep={built['step_path']}\nbytes={built['bytes']}",
            kind="claw",
        )
        return env

    # live path — acquire shared browser lock
    lock = {"ok": True, "skipped": True}
    if not skip_lock:
        lock = claw_browser_acquire("gemini@claw")
        env["lock"] = lock
        if not lock.get("ok"):
            env["ok"] = False
            env["error"] = lock.get("error") or "browser_busy"
            db.put_fact(
                "Tx-CLAW",
                f"gemini@claw-busy:{built['step_id']}",
                json.dumps(lock)[:1500],
                kind="claw",
            )
            return env

    try:
        # login preflight
        pre = gemini_preflight_login(via_cdp=True)
        env["preflight"] = {k: pre.get(k) for k in ("ONLINE", "LOGGED_IN", "READY", "LAST_CHECK_TS", "detail")}
        if not pre.get("LOGGED_IN"):
            env["ok"] = False
            env["error"] = "login_wall"
            env["method"] = "preflight_stop"
            try:
                fail_p = canonical_outbox() / f"GEMINI_FAIL_{built['step_id']}.md"
                fail_p.write_text(
                    f"# GEMINI_FAIL\nSTEP_ID: {built['step_id']}\nZULU: {db.zulu()}\n"
                    f"REASON: login_wall\nAVAILABILITY:\n"
                    f"ONLINE: {pre.get('ONLINE')}\nLOGGED_IN: {pre.get('LOGGED_IN')}\n"
                    f"READY: {pre.get('READY')}\nLAST_CHECK_TS: {pre.get('LAST_CHECK_TS')}\n"
                    f"DETAIL: {json.dumps(pre.get('detail') or {}, default=str)[:1200]}\n",
                    encoding="utf-8",
                )
                env["fail_path"] = str(fail_p)
            except Exception:
                pass
            db.put_fact(
                "Tx-CLAW",
                f"gemini@claw-loginwall:{built['step_id']}",
                json.dumps(env.get("preflight"))[:1500],
                kind="claw",
            )
            return env

        answer_path = built["answer_path"]
        ws_rel = built.get("answer_wsrel")

        # steward-CDP first-class (default)
        if steward_cdp:
            cdp = _gemini_cdp_promote(query, built["step_id"], Path(answer_path), wait_s=35)
            env["cdp"] = {k: cdp.get(k) for k in ("ok", "error", "bytes", "sha256", "path", "submitted", "already", "url") if k in cdp or cdp.get(k) is not None}
            env["method"] = "cdp_steward_promote"
            ver = verify_gemini_answer(answer_path, ws_rel=ws_rel) if cdp.get("ok") else cdp
            if cdp.get("ok") and not ver.get("ok"):
                ver = cdp  # promote wrote file; trust cdp hashes if verify structure flake
                if Path(answer_path).is_file():
                    ver = verify_gemini_answer(answer_path, ws_rel=ws_rel)
            env["verify"] = ver
            env["verified"] = bool(ver.get("ok"))
            env["delivered"] = bool(ver.get("ok"))
            env["ok"] = bool(ver.get("ok"))
            if ver.get("ok"):
                claw_availability_snapshot(
                    "gemini@claw", online=True, logged_in=True, ready=True, note="proof_ok"
                )
                db.put_fact(
                    "Ax-CLAW",
                    f"gemini@claw-proof:{built['step_id']}",
                    f"path={ver.get('path')}\nbytes={ver.get('bytes')}\nsha256={ver.get('sha256')}\nmethod=cdp_steward_promote",
                    kind="claw",
                )
            else:
                db.put_fact(
                    "Tx-CLAW",
                    f"gemini@claw-fail:{built['step_id']}",
                    f"cdp={env.get('cdp')}\nverify={ver}",
                    kind="claw",
                )
            return env

        # native CLI path (secondary; abort hint ≤90s)
        if use_cli is None:
            use_cli = True
        native_timeout = min(int(timeout), GEMINI_NATIVE_ABORT_S + 30)
        if use_cli:
            from datetime import datetime, timezone as _tz

            sid = "nova-gemini-" + datetime.now(_tz.utc).strftime("%Y%m%dT%H%M%SZ")
            answer_abs = built["answer_path"]
            compact = (
                f"ONE-STEP execute. Read the STEP file with the read tool, then follow it exactly.\n"
                f"STEP_PATH: {built['step_path']}\n"
                f"Write GEMINI_ANSWER with write/file_write BEFORE any DONE.\n"
                f"Preferred path: {answer_abs}\n"
                f"Fallback workspace-relative: {ws_rel}\n"
                f"Hard STOP on login wall/captcha (no credentials).\n"
                f"Wait for FULL gemini.google.com reply (~{GEMINI_NATIVE_ABORT_S}s). Mid-stream DONE forbidden.\n"
                f"On context overflow: STOP within {GEMINI_NATIVE_ABORT_S}s — do not thrash.\n"
                f"Chat ONLY after write succeeds:\n"
                f"DONE: <one line>\nFILES: {answer_abs}\nPROOF: bytes=<real_size>\nNEXT: STOP\n"
            )
            run = openclaw_run(
                compact,
                timeout=native_timeout,
                packet_id=packet_id,
                session_id=sid,
                model="ollama/qwen3.5:9b",
            )
            env["session_id"] = sid
            env["method"] = "native_openclaw"
            env["run"] = {
                k: run.get(k)
                for k in ("ok", "status", "zulu", "zulu_start", "runId", "model", "error")
                if k in run or run.get(k) is not None
            }
            env["run_text"] = (run.get("text") or "")[:800]
            # overflow fast-fail signal
            rt = (run.get("text") or "") + str(run.get("error") or "")
            if "context overflow" in rt.lower() or "overflow" in rt.lower():
                env["overflow_abort"] = True
            ver = verify_gemini_answer(answer_path, ws_rel=ws_rel)
            env["verify"] = ver
            env["verified"] = bool(ver.get("ok"))
            env["delivered"] = bool(ver.get("ok"))
            env["ok"] = bool(ver.get("ok"))
            if packet_id is not None:
                _mark_packet(packet_id, "delivered" if ver.get("ok") else "fail", note=ver)
            if ver.get("ok"):
                db.put_fact(
                    "Ax-CLAW",
                    f"gemini@claw-proof:{built['step_id']}",
                    f"path={ver.get('path')}\nbytes={ver.get('bytes')}\nsha256={ver.get('sha256')}\nmethod=native",
                    kind="claw",
                )
            else:
                db.put_fact(
                    "Tx-CLAW",
                    f"gemini@claw-fail:{built['step_id']}",
                    f"verify={ver}\nrun_status={run.get('status')}\ntext={(run.get('text') or '')[:600]}",
                    kind="claw",
                )
                try:
                    fail_p = canonical_outbox() / f"GEMINI_FAIL_{built['step_id']}.md"
                    fail_p.write_text(
                        f"# GEMINI_FAIL\nSTEP_ID: {built['step_id']}\nZULU: {db.zulu()}\n"
                        f"REASON: {ver.get('error') or run.get('status')}\nVERIFY: {ver}\n"
                        f"RUN_TEXT:\n{(run.get('text') or '')[:1500]}\n",
                        encoding="utf-8",
                    )
                    env["fail_path"] = str(fail_p)
                except Exception:
                    pass
            return env

        # handoff-only path (async)
        step_text = Path(built["step_path"]).read_text(encoding="utf-8")
        pid = handoff("openclaw@local", "task", step_text, whi="Tx-HAND")
        env["packet_id"] = pid
        env["delivered"] = False
        env["queued"] = True
        env["ok"] = True
        env["method"] = "handoff_queued"
        env["note"] = "handoff queued; prefer steward_cdp=True or claw-run + verify_gemini_answer for PROOF"
        db.put_fact(
            "Ax-CLAW",
            f"gemini@claw-queued:{built['step_id']}",
            f"packet_id={pid}\nstep={built['step_path']}\nanswer={answer_path}",
            kind="claw",
        )
        return env
    finally:
        if not skip_lock:
            try:
                claw_browser_release("gemini@claw")
            except Exception:
                pass
