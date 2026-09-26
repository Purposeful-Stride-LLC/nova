# Node mail-slot + talk/listen (lobster/komodo pattern)

Steward | 2026-09-21 ~04:41 CT | Ports locked 41776/41777 | Michael: address like mail; deploy via SSH; map node; LAN capture list

## Locked
- UDP **41776** ping/pong (Nova Mesh Beacon)
- TCP **41777** job RPC
- Non-colliding with ssh/ollama/tts/web

## Talk / listen = office mail, not a chat API

NOVA already talks to pets via **packets** (`office.post_packet` → inbox → `claw-run` / qwen).
Nodes get the **same shape**, different dest:

| Dest | Who | Transport |
|---|---|---|
| `openclaw@local` | Aurelius lobster | local CLI + PROOF |
| `qwen@local` | Komodo | local qwen hand |
| `node:og-ubuntu` | Tentacle on OG box | mesh TCP 41777 **or** SSH file mail-slot |
| `node:<id>` | Any wrapped host | same |

### Address
```
node:<id>           # tentacle (digester / senses / shell)
nova:<id>           # full peer palace (grade full)
hub:tuf             # this machine
```

Packet fields (mirror office):
```json
{
  "dest": "node:og-ubuntu",
  "kind": "task",
  "body": "digest_section | map_fs | holmes_sweep | still_cam | ...",
  "cite": "job:docs-ingest",
  "hil": false
}
```

**Listen (node):** mesh beacon thread + mail-slot `~/nova-tentacle/inbox/*.json` → `outbox/*.result.json`  
**Talk (hub):** `tentacle.submit` / `office.deliver` routes `node:*` through mesh (preferred) or SSH drop if mesh down.

Same leash instincts as lobster/komodo: allowlisted verbs, PROOF on file writes, HIL for mic/cam/mail/net outbound.

## Deploy path (once :22 open)
1. SSH key from TUF → `mike@192.168.0.76` (password was chat-temp only)
2. `mkdir ~/nova-tentacle/{inbox,outbox,bin,log}`
3. Install `tentacle_node.py` (beacon + mail-slot) — stub ready to push
4. systemd user service or `nohup` — Mike can start if needed
5. Hub job `tentacle-ping@90s` + route digests when TUF thermal denies

**Status now:** host pings; **:22 still closed** — cannot deploy until openssh-server enabled.

## Same tools, remote metal (CPU)
Node abilities to expose (map first, use second):
- `cpu_llm` — Ollama CPU digester (Claw-on-node noted weak; keep as optional `claw_host`)
- `shell` — allowlisted cmds
- `cam` / `mic` — still + PTT only, HIL from hub
- `net` — fetch only when hub packet says so
- `fs_map` — Holmes/Watson style inventory → paths into WHI as `Ax-NODE` / `Tx-NODE`

### Capture → WHI pathway
1. `map_fs` — find depth-N dirs/files (cat/list, not exfil secrets)
2. Hub organizes + chronicler summarizes interesting paths
3. Stamp `source_node=og-ubuntu` + full pathway in provenance header
4. Later: “how to utilize” brief (chamber topic) — **harness** homestead compute, not smash the box

Ubuntu = **different metal + different codebase** for her to learn: Linux paths, apt, systemd, CPU Ollama — homestead training for the next capture (console, phone, another PC).

## LAN scan (homestead awareness)
Whatever is on the LAN is a **candidate** after discover — not auto-wrap.

Job idea: `lan-scan@3600` (L0, extends thumb `lan_probe` / Holmes):
- ARP + ping sweep / mDNS names
- Tag classes: `pc`, `phone`, `console`, `iot`, `unknown`
- Open interesting ports (22, 41776, 11434, …) → inventory row `status: seen|reachable|wrapped`
- Gaming consoles / phones: list for **later bridge** (language/protocol gaps) — same capture list as OG once a tentacle exists

WHI: `Ax-LAN` facts for map; wrap only with Michael HIL.

## Build order (concrete)
1. Mike: enable sshd on OG (or yell when :22 open)
2. Deploy tentacle stub + key auth
3. Hub `nova/mesh` + `dest=node:*` in office/leash
4. Holmes/Watson remote `map_fs` → WHI pathways
5. Digest offload + thermal router
6. `lan-scan` standing job → capture backlog (consoles/phones/PCs)

## Exploit = utilize
All “exploit node resources” language here means **homestead utilization** under HIL — cam/mic/net gated, no unsupervised outbound.