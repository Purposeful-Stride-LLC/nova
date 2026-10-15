"""Named tentacle identity wrapper around nova.hearthbeat (Fieldkit 2.0)."""
from __future__ import annotations

from typing import Any

from nova import hearthbeat


class TentacleClient:
    """Thin named client for a tentacle node (Tentacle-01 homage defaults)."""

    def __init__(
        self,
        host: str = "192.0.2.10",
        node_id: str = "tentacle-01",
        from_id: str = "hub-01",
        display_name: str = "Tentacle-01",
        mail_address: str = "tentacle@tentacle-01",
    ) -> None:
        self.host = host
        self.node_id = node_id
        self.from_id = from_id
        self.display_name = display_name
        self.mail_address = mail_address

    def ping(self) -> dict:
        return hearthbeat.ping(host=self.host, from_id=self.from_id)

    def health(self) -> dict:
        return hearthbeat.submit({"kind": "health"}, host=self.host, timeout=30)

    def send_job(self, envelope: dict) -> dict:
        job = dict(envelope or {})
        job.setdefault("dest", self.mail_address)
        job.setdefault("to", self.node_id)
        return hearthbeat.submit(job, host=self.host)

    def poll_mail(self) -> dict:
        """Stub — wire later against hub mail.poll verb."""
        return {"ok": True, "queued": []}


def default_client() -> TentacleClient:
    """Default client pointing at OG / Tentacle-01."""
    return TentacleClient(
        host="192.0.2.10",
        node_id="tentacle-01",
        from_id="hub-01",
        display_name="Tentacle-01",
        mail_address="tentacle@tentacle-01",
    )


__all__ = ["TentacleClient", "default_client"]
