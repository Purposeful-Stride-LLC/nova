# NOVA setup guide for a Grok Bot

## Purpose
Step-by-step instructions a Grok Bot (an AI assistant with a shell on its owner's own Linux or Windows machine) can follow to install, test, and run NOVA using only this public repo. The bot sets things up and reports back; the owner makes every decision that matters.

## 1. Hardware / software check (report results to the owner)
- GPU: ~8 GB VRAM (RTX 5050 class) is enough for the default chat model `qwen3:8b`.
- RAM: 16 GB recommended; disk: ~10 GB free (model ~5 GB + venv + data).
- Python **3.10+** (`python --version`).
- [Ollama](https://ollama.com) listening on `127.0.0.1:11434`, with the model pulled: `ollama pull qwen3:8b`.
  Without Ollama the daemon and tests still run; only chat needs it.
- Ask the owner before any install that needs admin rights (Python, Ollama, GPU drivers).

Checks:
```bash
# Linux/macOS
python3 --version; nvidia-smi; df -h .; free -h
curl -s http://127.0.0.1:11434/api/tags
```
```powershell
# Windows PowerShell
python --version; nvidia-smi; Get-PSDrive C
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

## 2. Install
Linux/macOS (bash):
```bash
git clone https://github.com/Purposeful-Stride-LLC/nova.git
cd nova
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.txt pytest
mkdir -p data/config
cp config.example/*.json data/config/
```
Windows (PowerShell):
```powershell
git clone https://github.com/Purposeful-Stride-LLC/nova.git
cd nova
python -m venv .venv; .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt pytest
New-Item -ItemType Directory -Force data\config | Out-Null
Copy-Item config.example\*.json data\config\
```
Optional GUI: `python -m pip install PySide6` (not in `requirements.txt`).
`pytest` is also not in `requirements.txt`; install it for the tests.
If `data/config/*.json` already exists, **do not overwrite it** — it is the owner's config.

## 3. Run tests
```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q tests      # Linux/macOS
```
```powershell
$env:QT_QPA_PLATFORM="offscreen"; python -m pytest -q tests   # Windows
```
What passing looks like (clean Linux install, Python 3.13, no PySide6, no Ollama):
`46 passed, 13 skipped` — 12 skips are "PySide6 not installed", 1 is "not a staged kit". Skips for Windows-only, Qt, Ollama, or scratch-DB conditions are fine. Any **failure** must be reported to the owner.

## 4. Start NOVA (from the install folder)
```bash
python -m nova       # daemon: scheduler, DB writes, approved commands
python -m nova.tui   # terminal face; /cmd list, /cmd approve ID
python -m nova.gui   # read-only console (needs PySide6)
```
Windows: `START_NOVA.bat` / `START_GUI.bat`. Set `NOVA_HOME` to keep data elsewhere.
First daemon start creates `data/NOVA.db` (under `NOVA_HOME` if set).

## 5. Safety rules the bot must keep
- `net_allowlist` in `data/config/gates.json` stays **empty** until the owner adds hosts themselves.
- `enforce` in `data/config/governor.json` stays **false**.
- The LLM never commands actions; it only proposes.
- Every action is human-approved via `/cmd approve ID` — by the owner, not the bot.
- Never overwrite, delete, commit, upload, or ship anything in `data/`.
- Run one heavy GPU model at a time.
- Ask the owner before installs that need admin rights.

## 6. Verification checklist (report back to the owner)
- [ ] Python version, GPU/VRAM, free RAM and disk
- [ ] Ollama reachable at `127.0.0.1:11434`; `qwen3:8b` listed (or: not installed)
- [ ] `pip install -r requirements.txt` succeeded
- [ ] `data/config/gates.json` and `governor.json` present; allowlist `[]`; `enforce: false`
- [ ] Exact pytest line (passed / skipped / failed)
- [ ] Daemon started; `data/NOVA.db` created
- [ ] TUI opens and `/cmd list` works
- [ ] Anything that failed, with the error text

## 7. Undo / uninstall
- Stop the daemon/TUI/GUI (Ctrl+C).
- Delete the venv (`.venv`) and the install folder.
- `data/` (database and config) is the owner's: delete it **only with the owner's OK**. If `NOVA_HOME` was used, data lives there.
- Optional: `ollama rm qwen3:8b` (ask the owner).

## 8. Troubleshooting (seen in a clean test)
- GUI tests skipped / `ModuleNotFoundError: No module named 'PySide6'` → `pip install PySide6` (optional).
- `No module named pytest` → `pip install pytest`.
- Headless Linux Qt errors → set `QT_QPA_PLATFORM=offscreen`.
- `python -m nova` runs in the foreground and prints little; that is normal. Check that `data/NOVA.db` appears.
- Chat does nothing / connection refused → Ollama is not running or the model is not pulled.
