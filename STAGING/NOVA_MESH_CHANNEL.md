# Tentacle mesh channel + node grades

Steward | 2026-09-21 ~04:33 CT | Michael: custom ping channel; node vs full NOVA

## Problem
How do NOVA instances / tentacles **find and ping each other** without riding a *standard* channel that every scanner expects?

Stock ports we must **not** treat as the control plane:
- `:22` SSH â€” transport only (after key), not the ping protocol
- `:11434` Ollama â€” model API only
- `:8000` Pocket TTS â€” speak only
- plain HTTP `:80/:443` â€” too public / too â€œnormalâ€

Control plane = **our** channel: signed, allowlisted, boring-looking, easy to firewall.

## Recommendation: Nova Mesh Beacon (NMB)

### Channel choice
| Option | Verdict |
|---|---|
| A. UDP beacon on **nonstandard high port** (e.g. `41776/udp`) + TCP RPC on `41777/tcp` | **Pick for v1** â€” LAN only, no HTTP banner, easy allowlist |
| B. mDNS / `_nova._udp` | Nice later; noisy on some Wiâ€‘Fi APs |
| C. MQTT / Redis | Extra daemon; skip for homestead |
| D. Only SSH file drop | Works offline; too slow for heartbeat mesh |

**v1 listen:**
- `NMB_UDP_PORT=41776` â€” heartbeat / presence (JSON â‰¤512B)
- `NMB_TCP_PORT=41777` â€” job submit/collect (length-prefixed JSON)
- Bind `0.0.0.0` only behind host firewall allowlist from known peer CIDRs (home LAN)
- Optional shared secret HMAC in every frame (`mesh_psk` on TUF + node; never in palace text)

Port numbers are **config**, not magic â€” change per site if you want obscurity+allowlist.

### Why not â€œstandardâ€
A random high UDP/TCP pair doesnâ€™t look like web/ssh/ollama. Combined with:
- HMAC + node_id allowlist
- firewall: only TUF IP â†” OG IP
â€¦itâ€™s a private mesh, not an open service.

### Frame (UDP ping)
```json
{
  "v": 1,
  "kind": "ping",
  "from": "tuf-nova",
  "to": "og-ubuntu",
  "zulu": "2026-09-21T09:30:00Z",
  "grade": "hub|tentacle|full",
  "abilities": ["cpu_llm","shell"],
  "load": {"cpu":0.4,"ram":0.6},
  "ollama_n": 3,
  "mac": "<hmac>"
}
```
Reply `pong` same shape. Missed 3 intervals â†’ Ax-NODE stale.

### TCP job (digest)
Same as prior tentacle contract: `submit` / `collect` / `abort`.
SSH remains **bootstrap + key install + emergency shell**, not the chatty path.

## Node grades (what wraps what)

```
grade tentacle  â€” CPU (or weak GPU): digester only; WHI write-through to hub
grade full      â€” enough GPU + local NOVA.db + speak/RAG: peer palace
grade hub       â€” TUF today: source of truth, scheduler, thermal router
```

### Upgrade path (stops CPU thrashing)
1. **Tentacle** digests hard on CPU Ollama while hub is cool enough / busy GPU.
2. Build **local WHI RAG** on the node (read-replica or filtered chunk mirror).
3. When RAG hit-rate is good, **prefer retrieve-local** over re-digest â†’ CPU chill.
4. If GPU appears later (or metal is strong enough): promote inventory `grade: full`, run fieldkit subset (daemon + db + speak), mesh as peer â€” still HMAC to hub for HIL/outbound.

So: thrashing is a **bootstrap cost**; good WHI RAG is the **off-ramp**.

## Per-NOVA ownership
- Each hub may own **N tentacles** (inventory rows).
- A full peer is another hub-capable NOVA that **federates** facts (cite + hash), not one shared SQLite file over NFS.
- â€œEach nova can have a nodeâ€ = inventory + tentacle wrap; â€œfull implementationâ€ = grade promotion when metal qualifies.

## Code sketch (TUF)
```
nova/mesh/
  ports.py          # 41776/41777 defaults + env override
  crypto.py         # HMAC
  beacon.py         # UDP ping/pong L0
  rpc.py            # TCP submit/collect
  inventory.json    # peers: id, host, grade, abilities, last_pong
nova/tentacle/      # thin facade over mesh.rpc for digester jobs
```
Node: same `beacon` + `rpc` under `~/nova-tentacle/` (Python stdlib-first).

## Decide / lock
- **Channel:** UDP `41776` + TCP `41777` (site-configurable), HMAC, LAN firewall pair
- **SSH:** bootstrap only
- **Ollama:** payload plane only
- **Grade:** tentacle â†’ (RAG calm) â†’ optional full
- **WHI share:** packet protocol + provenance; not raw DB mount

## Next metal steps
1. OG `:22` + SSH key
2. Drop `~/nova-tentacle` beacon/rpc on Ubuntu
3. TUF `mesh` ping job @90s â†’ Ax-NODE
4. Route digest when `thermal.gate` denies local LLM

## Council
Topic packet when ports/PSK chosen and first ping lands â€” not a permanent seat.

## PORTS LOCKED 2026-09-21
Michael approved UDP 41776 + TCP 41777.
See also STAGING/NOVA_NODE_MAIL_AND_LAN.md (mail-slot addresses, SSH deploy, LAN capture list).
