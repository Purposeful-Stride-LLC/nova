# Hearthbeat Mail / Job Schema
Updated: 2026-09-22 06:02 CDT
Transport: UDP beacon **41776**, UDP jobs **41777**. Hub thin; tentacle mostly on OG `~/pg/nova-tentacle`. Node `hearth:og-ubuntu` @ 192.168.0.76 user mike.
No passwords/tokens in envelopes or palace text.

## Standard job envelope (JSON)
```json
{
  "id": "job-<uuid4>",
  "verb": "queue.ping|council.agenda|ingest.drain|leash.forge|step.execute|whi.gap_scout",
  "args": {},
  "timeout_s": 120,
  "proof_required": ["tree", "sha256"],
  "src": "hearth:tuf|hearth:og-ubuntu|steward",
  "dest": "tentacle@og|claw@local|qwen@local|brief@local",
  "priority": 5,
  "created_zulu": "2026-09-22T11:02:00Z",
  "not_before_zulu": null,
  "thermal_polite": true,
  "steward_run": false
}
```

### Field rules
| Field | Rule |
|-------|------|
| id | Globally unique; never reuse |
| verb | Dot-namespaced; unknown verb → failed + Tx-MAIL |
| args | JSON object only; no secrets |
| timeout_s | Hard wall; tentacle/Claw must stop |
| proof_required | Always include `tree` + `sha256` for write verbs |
| thermal_polite | If true, skip GPU work when hot |
| steward_run | Must be true for any LLM council run |

## Queue locations
### On hub (TUF fieldkit / palace)
- DB packets table (office mail): status `queued|running|done|failed`
- Filesystem (waiting work): `data/queue/waiting/`, `running/`, `done/`, `failed/`
- Board HTTP drain: separate `queue` table (URLs) — do not conflate with hearthbeat jobs

### On node (OG tentacle)
- `~/pg/nova-tentacle/queue/waiting|running|done|failed/`
- Mirror envelope filename: `<id>.json`
- Lid-closed: systemd + linger keeps tentacle taking jobs (see OG_LID_CLOSED_BEACON.md)

## Result format (Claw / tentacle MUST return)
```json
{
  "id": "job-<uuid4>",
  "ok": true,
  "zulu": "2026-09-22T11:02:00Z",
  "verb": "step.execute",
  "note": "short human line",
  "error": "",
  "proof": {
    "tree": ["relative/path:bytes", "..."],
    "sha256": {"relative/path": "hex..."},
    "bytes_total": 0
  },
  "artifacts": ["STAGING/...", "nova-out/..."],
  "whi": "Ax-CLAW|Tx-CLAW|Ax-TENTACLE|Tx-TENTACLE"
}
```

## Waiting work queue (gap close)
Michael named: **no waiting work queue**. Closing path:
1. Enqueue envelope → `data/queue/waiting/<id>.json`
2. Worker claims → atomic rename to `running/`
3. On success → `done/` + office packet status done + Ax-* fact
4. On fail/timeout → `failed/` + breaklog + Tx-*
5. Hub may UDP-push to OG 41777; OG may pull when beacon says alive

## Smoke verbs (no GPU)
- `queue.ping` — echo id, empty proof tree OK
- `council.agenda` — write NEXT_TOPIC advance only
