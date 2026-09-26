# NOVA Tentacles â€” distributed compute + shared WHI digester

Steward | 2026-09-21 ~04:30 CT | Michael clarified intent

## Point
A networked computer (first: OG Ubuntu @ LAN, CPU-only Ollama) is an **acquired resource**.
NOVA wraps it with a **tentacle** â€” thin code on TUF + a small agent face on the node â€” so she can:

1. **Distribute process jobs** (esp. knowledge digestion / chronicler summarize)
2. **Share WHI / palace state** (read/write facts+chunks with provenance, not a blind DB copy)
3. **Thrash the CPU node freely** while TUF GPU stays cool for speak / Claw / chamber
4. Scale the same pattern to the **next** Ollama host: another tentacle, same contract

This is computation distribution, not â€œSSH once and hope.â€

## Metaphor â†’ code
| Metaphor | Code |
|---|---|
| Tentacle | `nova/tentacle/` (TUF) + `~/nova-tentacle/` (node) |
| Wrap / leash | inventory + auth (SSH key) + heartbeat + job dispatch |
| Digestion | `docs-ingest` / `ingest-drain` workers that prefer `node:cpu` when gate says TUF warm |
| Shared WHI | sync protocol: export jobs + import accepted chunks with `source_node=` + `0x-DOC` / `Ax-NODE` |
| Next host | same tentacle class, new inventory row |

## What â€œshare the WHI databaseâ€ means (safe)
**Do not** mount or blindly replicate full `NOVA.db` over the LAN as the v1 design (corruption + lock + secret bleed).

v1 share:
- TUF is **source of truth** for live palace
- Tentacle pulls **work packets** (text sections + mask + min_score)
- Node runs small-model summarize on CPU Ollama
- Returns `{summary, model, mask, matrix_score?, cite, hash}` 
- TUF `store_accepted` stamps WHI + `source_node=og-ubuntu`

v2 (optional): read-replica SQLite snapshot of *public* chunk text for RAG-on-node; still write-through TUF only.

## Tentacle contract (minimal)
```
tentacle.ping(node_id) -> alive, load, ollama_tags, temp?
tentacle.submit(node_id, job) -> job_id
tentacle.collect(node_id, job_id) -> result | pending
tentacle.abilities(node_id) -> [cpu_llm, shell, mail_draft?, claw_host?]
```

Job kinds (first):
- `digest_section` â€” chronicler/analyst summarize one section
- `weigh_text` â€” matrix score if code-portable
- `codesum_path` â€” later
- `claw_step` â€” Aurelius via SSH only after pets drill

## Node side (â€œtentacle wrapâ€)
On Ubuntu:
- sshd + key auth (password was chat-only temp; never in palace)
- Ollama CPU
- `~/nova-tentacle/inbox/` + `outbox/` (or Cassiusâ€™s listener draft)
- optional tiny FastAPI later; files+SSH is enough for v1

## Thermal / scheduling
- TUF `thermal.gate("llm")` deny â†’ route digests to tentacle if `ping.ok` and node has tags
- Node may run hot â€” **thatâ€™s the point**; TUF stays cool
- Still: donâ€™t DOS the LAN; limit in-flight jobs (e.g. 1â€“2)

## Build order
1. ~~Profile stub~~ (host 192.168.0.76 user mike; :22 still closed last check)
2. sshd up + **SSH key** from TUF â†’ mike
3. `nova/tentacle/` L0 ping + submit/collect file protocol
4. Wire `docs-ingest` worker preference: `prefer=tentacle:og-ubuntu` when TUF warm or `force_distribute`
5. WHI import path stamps `source_node`
6. Job `tentacle-ping@900s` â†’ Ax-NODE
7. Next Ollama host = clone inventory row + same wrap

## Files
- This doc: `STAGING/NOVA_TENTACLE_DISTRIBUTED.md`
- Prior need: `STAGING/NEED_OG_UBUNTU_NODE.md` (still valid inventory)
- Profile: `STAGING/OG_UBUNTU_NODE_PROFILE.json`
- Listener draft (Cassius): `STAGING/OG_UBUNTU_INBOX_LISTENER_DRAFT.sh`

## Council
Topic packet when wiring starts â€” not a permanent seat.

## Mesh channel (follow-on)
See STAGING/NOVA_MESH_CHANNEL.md — custom UDP/TCP beacon, not stock ports; node grades tentacle→full.
