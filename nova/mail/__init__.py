"""NOVA mail package — TCP tentacle / hearthbeat shims (Fieldkit 2.0).

Real TCP lives in nova.hearthbeat. This package re-exports and adds
named TentacleClient identity helpers.
"""
from __future__ import annotations

from nova.hearthbeat import (
    BEACON_PORT,
    DEFAULT_HOST,
    JOB_PORT,
    MAX_FRAME,
    ping,
    smoke,
    submit,
)
from nova.mail.tentacle_client import TentacleClient, default_client
from nova.mail import claw_mail_tool  # Claw surface

__all__ = [
    "BEACON_PORT",
    "DEFAULT_HOST",
    "JOB_PORT",
    "MAX_FRAME",
    "TentacleClient",
    "default_client",
    "ping",
    "smoke",
    "submit",
    "claw_mail_tool",
]
