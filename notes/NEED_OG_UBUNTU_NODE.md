# Homestead need: OG Ubuntu compute node (LAN SSH)

Steward draft | 2026-09-21 ~04:20 CT | Michael approved draft

## Asset
- **Host:** Michael's older laptop (the OG box where he started with AI)
- **OS:** Ubuntu
- **GPU:** none â€” **CPU-only Ollama**
- **Models:** older / different tags than TUF (do not assume TUF jacket parity)
- **Link:** same LAN as TUF; SSH-capable
- **Role:** acquired **computation node** for NOVA â€” hear pings, answer, run work, optionally mail-bound tasks

## Intent
NOVA on TUF keeps the GPU palace / speak / Claw home base.
The Ubuntu node is a **leased worker**: SSH bridge + small agent face so she can:
1. Ping / heartbeat the node (alive? load? ollama tags?)
2. Dispatch CPU-cheap jobs (summarize, code lint, mail draft prep) without thrashing TUF VRAM
3. Optionally send **Aurelius (OpenClaw)** across the SSH bridge for hands-on work *on that box*
4. Return artifacts + PROOF back to TUF (`nova-out` / WHI stamp)

## Non-goals (v1)
- Not a second mind palace / not primary RAG store
- Not always-on STT or avatar
- Not unsupervised outbound mail (still HIL on TUF or explicit node policy)

## Shape (thin, like AiTutor / paper module)
```
TUF NOVA
  â”œâ”€â”€ nova/nodes/  (or nova/homestead/nodes.py)
  â”‚     inventory.json     # host id, lan ip/hostname, ssh user, role tags
  â”‚     ssh_bridge.py      # L0: check, run, scp pull/push â€” no LLM
  â”‚     ping.py            # heartbeat â†’ Ax-NODE fact
  â””â”€â”€ leash.dispatch_node(node_id, STEP)  # optional Claw-via-SSH
Ubuntu node
  â”œâ”€â”€ ollama (CPU)
  â”œâ”€â”€ thin listener OR just sshd + script inbox (~/nova-inbox/)
  â””â”€â”€ mail helpers only if HIL-gated from TUF
```

## Profile fields (inventory)
- `id`: e.g. `og-ubuntu`
- `os`, `arch`, `has_gpu`: false
- `ssh`: `{host, port, user, key_ref}` (key stays on TUF; never in palace text)
- `ollama`: `{base_url: localhost:11434 via ssh tunnel or remote}`, `tags[]` discovered live
- `abilities`: `[cpu_llm, shell, mail_draft?, claw_host?]`
- `WHI`: facts as `Ax-NODE` / probes as `Tx-NODE`

## Safety
- Same metal tree: one GPU consumer on TUF; Ubuntu is CPU-only so it **relieves** heat
- SSH commands allowlisted (no blind `rm -rf`); PROOF bytes=N on STEP done
- Secrets: SSH key / mail creds never logged into chunks
- First forge is **profile + ping only**; dispatch later with HIL

## Build order
1. Inventory stub + SSH reachability smoke from TUF
2. `ollama list` over SSH â†’ tag catalog (expect older models)
3. Heartbeat job on TUF (`node-ping@900s`) â†’ Ax-NODE
4. Inbox STEP drop (`~/nova-inbox/STEP_*.md`) + result pull
5. Optional: Claw remote session via SSH (after pets playbook drill)

## Cassius ask
Projects / tooling side: help profile the Ubuntu laptop (hostname, SSH user, key path, ollama tags) and sketch the thin inbox listener if you want something nicer than bare sshd. Varro owns TUF `nodes` + homestead need + leash hook.

## Council
Topic packet only â€” not a permanent seat. Drop STEP when wiring starts.

## Superseding vision
See STAGING/NOVA_TENTACLE_DISTRIBUTED.md — tentacle + shared WHI digester + multi-node Ollama wrap.
