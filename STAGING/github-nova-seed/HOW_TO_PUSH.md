# GitHub jargon + how to push NOVA’s README

## Tiny glossary

| Word | Means |
|---|---|
| **Repository (repo)** | A project folder GitHub stores, with history |
| **Organization (org)** | Company umbrella — ours is `Purposeful-Stride-LLC` |
| **Clone** | Download a copy of the repo to your computer |
| **Commit** | A saved snapshot (“save point”) with a message |
| **Push** | Upload your commits to GitHub |
| **Pull** | Download new commits from GitHub |
| **Remote / origin** | Nickname for “the GitHub copy”; usually called `origin` |
| **Branch** | A line of work; `main` is the default trunk |
| **README.md** | The front page GitHub shows for the repo |

## Easiest path (web UI — good for first time)

1. Open https://github.com/Purposeful-Stride-LLC  
2. **New repository**  
   - Name: `nova` (or `nova-fieldkit`)  
   - Private (recommended until you’re ready)  
   - **Add a README** — check the box, or leave empty and upload ours  
3. If empty: **Add file → Upload files** → drop `README.md` from  
   `Documents\NOVA\NOVA_fieldkit_v1_4\STAGING\github-nova-seed\README.md`  
4. Commit message: `Add NOVA README` → **Commit changes**

That’s a push without using the terminal.

## Terminal path (learning the jargon)

After the empty repo exists on GitHub (no README yet):

```powershell
# 1) Make a small folder that is ONLY what you want public
mkdir $env:USERPROFILE\src\nova-readme
cd $env:USERPROFILE\src\nova-readme
copy "Documents\NOVA\NOVA_fieldkit_v1_4\STAGING\github-nova-seed\README.md" .

# 2) Turn this folder into a git repo (local history)
git init
git branch -M main

# 3) Stage + commit (snapshot)
git add README.md
git commit -m "Add NOVA README"

# 4) Point at GitHub (remote named origin)
git remote add origin https://github.com/Purposeful-Stride-LLC/nova.git

# 5) Push (upload) — browser login may pop up
git push -u origin main
```

Replace `nova.git` with whatever you named the repo.

### Auth tip
GitHub no longer accepts account passwords for `git push`. Use:
- **GitHub CLI** (`gh auth login`), or  
- **Personal Access Token** as the password, or  
- **SSH key** (`git@github.com:Purposeful-Stride-LLC/nova.git`)

Frontinus2 (Google) can sign the web UI; for command line, one-time `gh auth login` is easiest once installed.

## Do not push

- Whole `NOVA_fieldkit_v1_4` until a real `.gitignore` exists  
- `NOVA.db`, logs with secrets, `GrokBot.log.ai` if sensitive  
- Anything under Documents IP / patents unless intentional

## Next after README

Add `LICENSE`, then carefully publish selected `STAGING` docs — or keep the heavy field kit private and this repo as the public face.
