"""Portable path resolution for NOVA fieldkit 2.1.

Nothing here hardcodes a user name or drive. Every path resolves from:
  1. NOVA_HOME (data root; see db.home()), or the kit beside this package (__file__);
  2. optional overrides in <NOVA_HOME>/data/config/paths.json;
  3. optional env vars (NOVA_DOCS_ROOT, NOVA_THUMB_AI, NOVA_AVATAR_ROOT, NOVA_STEWARD_LOG,
     COMFYUI_ROOT, OPENCLAW_CLI).
A missing optional root resolves to None; callers must skip it rather than guess.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # the install folder that holds nova/


def home() -> Path:
    from nova import db
    return db.home()


def _cfg() -> dict:
    try:
        p = home() / "data" / "config" / "paths.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except Exception:
        return {}


def _opt(key: str, env: str) -> Path | None:
    v = os.environ.get(env) or _cfg().get(key)
    return Path(v).expanduser() if v else None


def kit_root() -> Path:
    return KIT


def nova_parent() -> Path:
    """Folder that holds the fieldkit installs (sibling of the kit)."""
    return KIT.parent


def docs_root() -> Path | None:
    """Operator documents root for docs-ingest. Default: the folder above the NOVA parent."""
    return _opt("docs_root", "NOVA_DOCS_ROOT") or nova_parent().parent


def thumb_ai() -> Path | None:
    return _opt("thumb_ai", "NOVA_THUMB_AI")


def avatar_root() -> Path | None:
    p = _opt("avatar_root", "NOVA_AVATAR_ROOT")
    if p:
        return p
    t = thumb_ai()
    return (t / "nova-ai" / "agents" / "avatar") if t else None


def comfyui_root() -> Path | None:
    return _opt("comfyui_root", "COMFYUI_ROOT")


def steward_log() -> Path:
    """Steward mirror log. Defaults INSIDE NOVA_HOME so a staged/scratch home never touches live files."""
    return _opt("steward_log", "NOVA_STEWARD_LOG") or (home() / "nova-out" / "GrokBot.log.ai")


def openclaw_cli() -> str | None:
    v = os.environ.get("OPENCLAW_CLI") or _cfg().get("openclaw_cli")
    if v:
        return v
    w = shutil.which("openclaw")
    if w:
        return w
    appdata = os.environ.get("APPDATA")
    if appdata:
        c = Path(appdata) / "npm" / "openclaw.CMD"
        if c.is_file():
            return str(c)
    return None


def openclaw_workspace() -> Path:
    return Path.home() / ".openclaw" / "workspace"


def watson_roots() -> list[Path]:
    """Roots Watson may map. Opt-in list from paths.json; default is only NOVA_HOME."""
    roots = [home()]
    for r in _cfg().get("watson_roots") or []:
        roots.append(Path(r).expanduser())
    return roots
