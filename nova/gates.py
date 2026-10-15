"""Brutus-style gates for NOVA 2.1 (scope allowlist, refuse on unknown, fail closed, ack).

Pattern (from the Brutus wardog): no scope -> refuse; unknown target -> refuse; a check that
cannot complete -> refuse (fail closed); a human ack is the release. Every decision is logged
to data/gates/gates.jsonl so the operator can audit refusals.

Config: <NOVA_HOME>/data/config/gates.json (see DEFAULTS). Missing/bad config -> DEFAULTS,
which REFUSE all network hosts (empty allowlist).
"""
from __future__ import annotations

import fnmatch
import json
import time
from pathlib import Path
from urllib.parse import urlparse

DEFAULTS: dict = {
    # Network scope for /web, crawl, board drain, docs-scout URLs. Empty = refuse everything.
    "net_allowlist": [],
    # Chat may only PROPOSE these command verbs into the inbox. Anything else is refused.
    "chat_scope": ["job.pause", "job.resume", "job.run_now", "report.approve", "report.close",
                   "url.approve", "url.deny"],
    # Chat proposals need an explicit operator ack (approve) before the daemon runs them.
    "chat_requires_ack": True,
}


def _home() -> Path:
    from nova import db
    return db.home()


def config() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))
    p = _home() / "data" / "config" / "gates.json"
    try:
        if p.is_file():
            over = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(over, dict):
                cfg.update(over)
    except Exception as exc:  # bad json -> defaults (which refuse)
        cfg["_config_error"] = str(exc)[:120]
    return cfg


def audit(ev: dict) -> None:
    try:
        d = _home() / "data" / "gates"
        d.mkdir(parents=True, exist_ok=True)
        ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **ev}
        with (d / "gates.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=True) + "\n")
    except OSError:
        pass


def host_allowed(url: str, cfg: dict | None = None) -> dict:
    """Return {allow, reason, host}. Unknown host, bad URL, or empty scope -> refuse."""
    try:
        cfg = cfg or config()
        u = urlparse((url or "").strip())
        if u.scheme not in ("http", "https") or not u.hostname:
            r = {"allow": False, "reason": "bad_url", "host": None}
        else:
            host = u.hostname.lower()
            pats = [str(p).lower() for p in cfg.get("net_allowlist") or []]
            if not pats:
                r = {"allow": False, "reason": "NOVA REFUSES: empty net_allowlist (no scope)", "host": host}
            elif any(host == p or fnmatch.fnmatch(host, p) for p in pats):
                r = {"allow": True, "reason": "allowlisted", "host": host}
            else:
                r = {"allow": False, "reason": "NOVA REFUSES: host not on net_allowlist", "host": host}
    except Exception as exc:  # fail closed
        r = {"allow": False, "reason": f"gate_error:{exc}", "host": None}
    if not r["allow"]:
        audit({"gate": "net", "url": (url or "")[:200], **r})
    return r


def chat_command_allowed(verb: str, cfg: dict | None = None) -> dict:
    try:
        cfg = cfg or config()
        ok = verb in (cfg.get("chat_scope") or [])
        r = {"allow": ok, "reason": "in chat_scope" if ok else "NOVA REFUSES: verb outside chat_scope",
             "needs_ack": bool(cfg.get("chat_requires_ack", True))}
    except Exception as exc:
        r = {"allow": False, "reason": f"gate_error:{exc}", "needs_ack": True}
    if not r["allow"]:
        audit({"gate": "chat_scope", "verb": verb, **r})
    return r
