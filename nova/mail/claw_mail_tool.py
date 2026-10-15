"""Thin Claw-callable tentacle mail tool over TCP hearthbeat (Fieldkit 2.0).

Claw / OpenClaw agents import this module — do not edit OG tentacle code.
Defaults: Tentacle-01 @ 192.0.2.10 beacon 41776 / jobs 41777.
"""
from __future__ import annotations

from typing import Any

from nova.mail.tentacle_client import TentacleClient, default_client

__all__ = [
    "ping",
    "health",
    "send_job",
    "poll_mail",
    "default_tool_client",
    "dry_run_ping",
]


def default_tool_client() -> TentacleClient:
    return default_client()


def ping(client: TentacleClient | None = None) -> dict:
    """Beacon ping → pong. LAN required."""
    c = client or default_tool_client()
    return c.ping()


def health(client: TentacleClient | None = None) -> dict:
    """Submit kind=health job on 41777."""
    c = client or default_tool_client()
    return c.health()


def send_job(envelope: dict, client: TentacleClient | None = None) -> dict:
    """Submit a job envelope to the tentacle. No secrets in envelope."""
    c = client or default_tool_client()
    job = dict(envelope or {})
    # Strip common secret-ish keys if present (defense in depth)
    for bad in ("password", "token", "api_key", "secret", "authorization"):
        job.pop(bad, None)
    return c.send_job(job)


def poll_mail(client: TentacleClient | None = None) -> dict:
    """Poll hub/tentacle mail queue.

    Uses TentacleClient.poll_mail stub today; when OG schema exposes mail.poll,
    the client method becomes real without changing this Claw surface.
    """
    c = client or default_tool_client()
    return c.poll_mail()


def dry_run_ping(host: str = "192.0.2.10", timeout: float = 5.0) -> dict:
    """Non-raising connectivity probe for smoke / STAGING PROOF."""
    import socket

    from nova import hearthbeat

    try:
        pong = hearthbeat.ping(host=host, timeout=timeout, from_id="claw-mail-tool")
        return {"ok": True, "reachable": True, "host": host, "pong": pong}
    except (OSError, socket.timeout, ConnectionError, ValueError) as exc:
        return {
            "ok": False,
            "reachable": False,
            "host": host,
            "error": type(exc).__name__ + ": " + str(exc)[:200],
        }
