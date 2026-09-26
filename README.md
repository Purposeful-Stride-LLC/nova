# NOVA

**Homestead AI that lives on your metal** — a local-first field kit with a mind-palace memory, leashed pets, and room to grow tentacles across the LAN.

> Copyright © 2026 Purposeful Stride LLC. All rights reserved.  
> Org: [Purposeful-Stride-LLC](https://github.com/Purposeful-Stride-LLC)

## What NOVA is

NOVA is not a cloud chatbot wrapper. It is a **sovereign assistant stack** you run yourself: daemon jobs, a searchable palace, optional GUI chrome, and human-in-the-loop gates for anything that leaves the machine.

| Piece | Plain meaning |
|---|---|
| **Palace** | Local memory database (`NOVA.db`) — facts and text chunks she can search |
| **WHI** | Provenance labels on knowledge (What / How / Where / Why style codes) so RAG stays trustworthy |
| **Daemon / jobs** | Background timers — ingest, maintain, camera stills, thermal checks, council stubs |
| **Pets** | Leashed helpers — Aurelius (OpenClaw), Komodo (Qwen / code), Pocket TTS (voice) |
| **Hearthbeat** | LAN mesh beacon so a hub NOVA can see slave **tentacle** nodes |
| **HIL** | Human-in-the-loop — mic, mail, outbound net need your OK |

## Repo contents

| Path | Role |
|---|---|
| `nova/` | Python package — sched, ingest, WHI, thermal, leash, TUI, GUI |
| `STAGING/` | Plans, reports, acquisition profiles, GUI art mint scripts |
| `docs/` | Human how-tos (push, pets, GUI art, missing-steps order) |
| `data/` | Queue layout and reference stubs (no live DB or secrets) |
| `ascii/` | Light brand art for the TUI |
| `TUTORIAL.md` | Streamlined human tutorial |
| `DEVLOG.md` | Public chronicle of eras (metal-loop detail stays in `DEVLOG.txt`) |

**Not** in this repo: live `NOVA.db`, `.env` keys, SSH passwords, mesh PSKs, or GUI `.wav` beds.

## Quick start

Typical Windows field kit:

```text
Documents/NOVA/NOVA_fieldkit_v1_4
```

```powershell
cd Documents\NOVA\NOVA_fieldkit_v1_4
python -m nova          # daemon
python -m nova.tui      # metal face
python -m nova.gui      # optional PySide6 client
# Or: START_NOVA.bat  (TTS serve + daemon + GUI)
```

Needs a local Ollama (or compatible) endpoint for chat. Pocket TTS default voice is **anna**. See `TUTORIAL.md` for slash commands and safety pages.

## Safety

- One heavy GPU consumer at a time on modest laptops; thermal gates skip LLM work when the card is hot.
- Slave tentacles may thrash CPU on purpose (digest / scout) — that is by design.
- Never commit `.env`, API keys, SSH private keys, `NOVA.db`, or `*.wav` music beds.
- Outbound mail, mic, and WhatsApp-style bridges stay behind HIL approval.

## Status as of 2026-09-26

- **GUI chrome + music minted** — four theme backgrounds under `STAGING/gui_art/`; music beds minted via `STAGING/mint_gui_assets.py` (WAVs stay local / gitignored).
- **Diffusers paint path** working for SD1.5 backgrounds when ComfyUI is blocked.
- **OG tentacle** — first Linux hearthbeat node profiled; WHI drain / daily haul paced to connection.
- **OpenClaw / Aurelius** — gateway + leash handoff in use; PROOF-before-DONE rule for pet forges.
- **Comfy AppLocker note** — on some Windows hosts, Application Control can block ComfyUI high-side DLLs; Diffusers is the fallback paint lane. Details in `docs/REPORT_GUI_ART_MUSIC_HOWTO_2026-09-26.md`.

## Related sites

- [NOVA Command](https://ivory-jolly-sapphire-lark.grok.me/)
- [Frostshield](https://zippy-trail-apex-zinc.grok.me/)
- [FRONTINUS](https://solar-crisp-palm-fire.grok.me/)

## Ownership & license

All code and docs in this repository are **© Purposeful Stride LLC**. See [`LICENSE`](LICENSE) — proprietary, All Rights Reserved. Public visibility is for inspiration and education; it does not waive rights or grant patents or trademarks.

## Contributing

Issues and discussion welcome on the [Purposeful-Stride-LLC](https://github.com/Purposeful-Stride-LLC) organization. Please open an issue before large PRs. Do not submit secrets, live databases, or third-party proprietary dumps.
