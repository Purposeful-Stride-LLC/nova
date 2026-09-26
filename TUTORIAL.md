# NOVA Tutorial

Parse-friendly human guide. Examples start with `>> `.  
Canonical field-kit path (generic):

```text
Documents/NOVA/NOVA_fieldkit_v1_4
```

`TUTORIAL.txt` is a short pointer to this file for older TUI `/tutorial` readers.

---

## PAGE 1 — Boot

Need three processes eventually. Two are enough to talk.

```powershell
cd Documents\NOVA\NOVA_fieldkit_v1_4
python -m nova
python -m nova.tui
python -m pocket_tts serve --default-voice anna
# Or: START_NOVA.bat  (titled TTS window + daemon + GUI)
```

>> `/help`  
Expect: slash list in the chat and the right pane.

>> `/tutorial 2`  
Expect: page 2. Plain "next page 2" also works.

---

## PAGE 2 — Orient

>> `/tools` — short hand list.  
>> `/forge` — `job=` string + cite for each hand.  
>> `/suggest` — ready-to-paste `/job add SECS name`.  
>> `/list` — same as `/tools`.

---

## PAGE 3 — Jobs and daemon

>> `/jobs` — id, name, every_s, enabled, last_err.  
>> `/job add 300 holmes` — `JOB ADD <id>`.  
>> `/job on 1` / `/job off 1` / `/tick` — due jobs run now; daemon window prints dicts.

Robust cases:

```text
/job add 600 hw-check
/job add 600 ollama-catalog
/job add 900 whistle
/job add 300 cam:0
/job add 3600 web:https://example.com
```

---

## PAGE 4 — Models and staff

>> `/models` — local tags; binds staff rows (masks, not Modelfile jackets).  
>> `/staff` — e.g. `brief@local v=anna model=qwen3:8b`.  
>> `/model <tag>` — next `/ask` uses that tag.  
>> `/mask list` / `/mask auto` / `/mask <name>` — activation cues in `nova/masks.py`.

---

## PAGE 5 — Web and hunt

>> `/web https://example.com` — ingest true/false, score, path under `data/artifacts/`.  
>> `/hunt example` — palace rows, no LLM.  
JS-heavy homepages often `Tx-REJECT` — that is the gate working.

>> `/crawl https://docs.python.org/3/` — same-host explore; daemon can drain the board.

---

## PAGE 6 — PDF, history, cam

>> `/pdf path/to/paper.pdf` — `Tx-PDF` + text artifact, or "no text layer".  
>> `/history` — browser History copy → `Tx-HIST` (close the browser if locked).  
>> `/codesum nova` — inventory of `nova/*.py` (Ollama up; long run).  
>> `/cam 0` — still under artifacts, or OpenCV missing / no frame.

---

## PAGE 7 — Speak / TTS (Pocket TTS, voice anna)

>> `/tts Queue is law.` — wav under artifacts if serve is up.  
>> `/voice anna`  
Model may emit `[speak anna] ... [/speak]`; the parser peels that after `/ask`.  
Serve default: `http://127.0.0.1:8000`. Prefer serve-not-generate.

---

## PAGE 8 — Hunt / WHI

Facts and chunks carry WHI wings. Indexes keep provenance searchable.

>> `/hunt Ax-CHAMBER` — chamber motion stamps.  
>> `/hunt Tx-TEMP` — unpromoted council opinions (not in `/rag` until promote).  
>> `/rag <query>` — live chunks only, tiny-model INCLUDE/EXCLUDE gate.

---

## PAGE 9 — Tentacle / Hearthbeat (high level)

Hearthbeat is the LAN mesh: UDP beacon so a hub NOVA sees slave **tentacle** nodes. Jobs can move digest/scout work off the GPU laptop onto a CPU box.  
Doctrine and acquisition profiles live under `STAGING/acquisition/` and `docs/`. Do not put passwords or private keys in the tree — use env vars / local secrets.

---

## PAGE 10 — GUI themes and music

```powershell
python -m nova.gui
```

Theme backgrounds live under `STAGING/gui_art/` (PNGs are in git).  
Mint / refresh assets with `STAGING/mint_gui_assets.py` (and Diffusers helper `STAGING/mint_gui_diffusers.py` when ComfyUI is blocked).  
**WAV music beds are not in git** — they land under `STAGING/gui_music/` locally. See `docs/REPORT_GUI_ART_MUSIC_HOWTO_2026-09-26.md`.

---

## PAGE 11 — Safety / HIL

- Mic, mail, outbound net, and WhatsApp-style bridges need human approval.  
- One heavy GPU consumer at a time on modest cards; thermal gates skip LLM when hot.  
- Never commit `.env`, API keys, SSH keys, `NOVA.db`, or `*.wav`.  
- Claw STEPs: **Ack is not DONE** — require PROOF (bytes / tree / hash) before promote.

---

## Command index (machine)

`/help` `/tutorial` `/tools` `/forge` `/suggest` `/list` `/jobs` `/job` `/tick`  
`/web` `/hunt` `/pdf` `/codesum` `/history` `/models` `/model` `/mask` `/conv`  
`/holmes` `/queue` `/approve` `/deny` `/reports` `/ack` `/staff` `/tts` `/voice`  
`/cam` `/see` `/hear` `/vision` `/crawl` `/rag` `/chamber` `/quit`

## Dependents

- Python ≥ 3.10, Ollama `:11434`, pocket-tts serve `:8000` (voice anna)  
- Optional: psutil, opencv-python-headless, pypdf, PySide6 (GUI)

## Cites

- [Ollama docs](https://ollama.com/docs)  
- [Pocket TTS serve](https://kyutai-labs.github.io/pocket-tts/CLI%20Commands/serve/)  
- [pypdf](https://pypdf.readthedocs.io) · [OpenCV](https://docs.opencv.org)
