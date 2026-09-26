# NOVA

**Homestead AI for Purposeful Stride LLC** — a field kit that lives on your metal, remembers with WHI provenance, and can grow tentacles to other computers on the LAN.

> Owner org: [Purposeful-Stride-LLC](https://github.com/Purposeful-Stride-LLC)  
> Personal owner key: `Frontinus2` (Mikey D)

## What it is

NOVA is a **local-first** assistant stack (not a cloud chatbot wrapper):

| Piece | Plain meaning |
|---|---|
| **Palace** | Her memory database (`NOVA.db`) — facts and text chunks she can search |
| **WHI** | Labels on knowledge (What/How/Where/Why style codes like `0x-DOC`) so RAG stays trustworthy |
| **Daemon / jobs** | Background timers (ingest, maintain, camera stills, thermal checks) |
| **Pets** | Leashed helpers — Aurelius (OpenClaw / “lobster”), Komodo (Qwen / code), Pocket TTS (voice) |
| **Hearthbeat** | LAN mesh beacon (UDP 41776/41777) so a hub NOVA can see slave **tentacle** nodes |
| **HIL** | Human-in-the-loop — mic, mail, outbound net need your OK |

Primary metal today: **TUF** (Windows + NVIDIA). First slave node: **LinuxBox1** (`hearth:og-ubuntu`) for CPU digest/scout so the laptop GPU stays cool.

Related company sites: [NOVA Command](https://ivory-jolly-sapphire-lark.grok.me/), [Frostshield](https://zippy-trail-apex-zinc.grok.me/), [FRONTINUS](https://solar-crisp-palm-fire.grok.me/).

## What this repo is for

Shareable **docs and public-safe layout** for the NOVA field kit:

- Architecture notes and status handoffs
- How to run / schedule jobs (high level)
- Hearthbeat / tentacle concepts
- Links to AiTutor courses (Projects tree stays separate)

**Not** for secrets, live databases, SSH passwords, mesh PSKs, or private Documents IP dumps.

## Quick map (field kit on disk)

Typical Windows install lives under something like:

`Documents/NOVA/NOVA_fieldkit_v1_4/`

| Path | Role |
|---|---|
| `nova/` | Python package — sched, ingest, WHI, thermal, leash, … |
| `STAGING/` | Plans and reports (working papers) |
| `nova-out/` | Steward / pet outputs |
| `TUTORIAL.txt` | In-app tutorial pages |

Thumb drive shards (`D:\pg\ai`) are **legacy**; intentional knowledge feed is Documents → WHI.

## Safety notes

- One GPU consumer at a time on TUF; thermal gate skips LLM when the card is hot
- Slave nodes may thrash CPU on purpose (digest/scout)
- Never commit `.env`, API keys, SSH private keys, or `NOVA.db`

## Status (2026-09-21)

- Mind-palace Documents ingest Day 1–3 + AiTutor `gzu-dscl` course stamped `0x-DOC`
- Hearthbeat tentacle live on OG Ubuntu
- Avatar / paint / WhatsApp parked; see `STAGING/NOVA_STATUS_HANDOFF_2026-09-21.md` on the field kit

## License / contact

Copyright © Purposeful Stride LLC. All rights reserved unless a LICENSE file says otherwise.

Issues and collaboration: use this GitHub Organization.
