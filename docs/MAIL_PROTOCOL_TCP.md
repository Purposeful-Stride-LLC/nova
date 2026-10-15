# NOVA Mail Protocol — TCP Standard (Fieldkit 2.0)
**Locked:** 2026-09-27  
**Supersedes:** UDP wording in older HEARTHBEAT notes  
**Live proof:** OG tentacle `tentacle-01` / 192.0.2.10 — `bin/tentacle_node.py`

---

## Transport

| Port | Role | Framing |
|--|--|--|
| **TCP 41776** | Beacon | 4-byte big-endian length + UTF-8 JSON |
| **TCP 41777** | Jobs / mail | same framing |

SSH is **steward wrench only** (deploy, debug). Runtime mesh is this TCP mail.

Max frame: 8_000_000 bytes. Oversized results spill to `outbox/<job_id>.result.json` and return a path stub.

---

## Identity

Every tentacle declares:

```json
{
  "node_id": "tentacle-01",
  "display_name": "Tentacle-01",
  "mail": "tentacle@tentacle-01",
  "grade": "tentacle",
  "lan": "192.0.2.10"
}
```

Hub mail names stay: `brief@local`, `openclaw@local`, `qwen@local`, `tentacle@tentacle-01`, …

Poll rate: tentacle asks hub for mail **every 30–60 seconds** (1–2×/min).

---

## Beacon (41776)

Request: `{ "kind": "ping", "from": "hearth:hub-01", "zulu": "..." }`  
Reply: `{ "v":1, "kind":"pong", "from":"tentacle-01", "grade":"tentacle", "abilities":[...], "load":{...}, "mem":{...}, "job_tcp":41777, "beacon_tcp":41776, "proto":"tcp" }`

Optional HMAC: `mac` = first 16 hex of HMAC-SHA256(PSK, body) — homestead PSK via env `NOVA_MESH_PSK` (never in palace text).

---

## Job envelope (41777)

Align with `HEARTHBEAT_MAIL_JOB_SCHEMA.md` verbs; wire over TCP:

```json
{
  "id": "job-<uuid4>",
  "kind": "ping|discover|ollama_gen|map_fs|sys_inventory|whi.research_packet|mail.poll|mail.deliver",
  "verb": "queue.ping",
  "args": {},
  "timeout_s": 120,
  "proof_required": ["tree", "sha256"],
  "src": "hearth:hub-01",
  "dest": "tentacle@tentacle-01",
  "priority": 5,
  "created_zulu": "...",
  "thermal_polite": true,
  "steward_run": false
}
```

`kind` is what live `tentacle_node.py` switches on today; `verb` is the Fieldkit 2.0 namespaced name — prefer both during transition.

Result:

```json
{
  "ok": true,
  "job_id": "job-...",
  "kind": "...",
  "zulu": "...",
  "ms": 12,
  "proof": { "tree": [], "sha256": {}, "bytes_total": 0 },
  "whi": "Ax-TENTACLE"
}
```

---

## OpenClaw tool (hub)

Claw gets a **tentacle mail** tool (not SSH):

1. `tentacle.ping(node)` → beacon 41776  
2. `tentacle.send_job(node, envelope)` → 41777  
3. `tentacle.poll_mail(node)` / hub `mail.poll` every ~45s  
4. Haul `outbox/DRAIN_BATCH_*.json` → palace only after steward PROOF

Leash rules unchanged: write verbs need PROOF tree + sha256.

---

## Local WHI on tentacle

- DB: `~/pg/nova-tentacle/whi/NOVA_NODE.db`  
- Queue: `queue/waiting|done|failed` subject JSON  
- Outbox batches for hub haul  
- Origins/timestamps required on every packet (Fieldkit 2.0 harden)

---

## Security

- Bind LAN; hub allowlist  
- No secrets in envelopes or beacon  
- UFW: 41776/41777 from LAN only when sudo available  
- One systemd `nova-tentacle.service` (no duplicate manual processes)

---

## Doc debt closed by this file

Older STAGING notes saying **UDP** 41776/41777 are obsolete for OG. Keep filename HEARTHBEAT; transport is TCP.
