# How to push NOVA (org repo)

## Tiny glossary

| Word | Means |
|---|---|
| **Repository (repo)** | A project folder GitHub stores, with history |
| **Organization (org)** | Company umbrella — ours is `Purposeful-Stride-LLC` |
| **Clone** | Download a copy of the repo to your computer |
| **Commit** | A saved snapshot with a message |
| **Push** | Upload your commits to GitHub |
| **Pull** | Download new commits from GitHub |
| **Remote / origin** | Nickname for the GitHub copy |
| **Branch** | A line of work; `main` is the default trunk |
| **README.md** | The front page GitHub shows for the repo |

## Repo

Public / org face: https://github.com/Purposeful-Stride-LLC/nova

This tree is meant to be the shareable field-kit face: docs, package, STAGING plans, GUI art PNGs. Live databases and secrets stay off git (see `.gitignore` and `LICENSE`).

## Terminal path (after a local commit is ready)

```powershell
cd path\to\nova
git status
git add -A
git status   # review — no .env, no .db, no .wav, no secrets
git commit -m "Describe the change"
git push -u origin main
```

Replace `main` if your default branch differs. Prefer reviewing `git status` twice before the first public push.

## Auth (no tokens in this file)

GitHub does not accept account passwords for `git push`. Use one of:

- **GitHub CLI** — `gh auth login` (easiest once installed)
- **SSH remote** — `git@github.com:Purposeful-Stride-LLC/nova.git`
- **Personal Access Token** via your credential helper (store it in the OS keychain, never in the repo)

Never paste PATs, cookies, or SSH private keys into markdown, STAGING, or commit messages.

## Do not push

- Live `NOVA.db`, `.env`, `*.pem`, `*.key`, mesh PSKs
- `GrokBot.log.ai` or logs that may contain secrets
- `*.wav` GUI music beds (mint locally; PNGs are OK)
- Hardcoded SSH passwords in one-off STAGING scripts (use env vars)
- Whole Documents / patent trees unless intentional and licensed

## After push

Confirm the GitHub org page shows `README.md`, `LICENSE`, and that Actions / secret scanning (if enabled) stay clean. Issues welcome on the org.
