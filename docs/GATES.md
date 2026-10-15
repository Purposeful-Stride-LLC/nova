# NOVA fieldkit 2.1 — Gates (Brutus pattern)

The rule is borrowed from the Brutus wardog. No scope means **refuse**. An unknown target means
**refuse**. A check that cannot complete means **refuse** (fail closed). A human ack is the release.
Every refusal is logged to `<NOVA_HOME>/data/gates/gates.jsonl`.

## 1. Network scope allowlist (`nova/gates.py`)
`<NOVA_HOME>/data/config/gates.json`:
```json
{"net_allowlist": ["docs.python.org", "*.wikipedia.org"]}
```
* This applies to `/web` (hands/web.fetch), crawl start and every crawled page, and the board drain.
* An **empty or missing allowlist refuses all hosts** (`NOVA REFUSES: empty net_allowlist`). This
  is the 2.1 default, so the operator has to opt hosts in before any fetch.
* Bad JSON gives the defaults, which refuse. Non-http(s) URLs are refused.

## 2. HIL on URL ingest
`queued` means "awaiting approval". `board.drain_one` fetches only `approved` rows, and the host
must also pass the allowlist.

## 3. Chat command scope + ack
Chat cannot act. It may only *propose* verbs listed in `chat_scope` (default: job pause/resume/run-now,
report approve/close, url approve/deny). Anything else is refused at propose time. With
`chat_requires_ack: true` (the default) a chat proposal waits in `proposed/` until the operator
approves it. Code guards after the model (`nova/chat.py`):
* speak tags are dropped when Voice is not UP, and on status, refusal, self, voice and proposal answers;
* job names in commands are rewritten to ids (`/job off cam:0` → `/job off 4`);
* a commanded job change for a non-job request is removed;
* "I paused / sent / deleted…" claims are removed and replaced by "Not done: …";
* a voice answer that contradicts the SELF Voice line is replaced by that line.

## 4. Governor enforce mode (`nova/governor.py`)
`data/config/governor.json` → `"enforce": false` (the default, **unchanged**: dry-run).
* `python -m nova.governor report` writes `data/governor/governor_dryrun_report.json`. It lists what
  enforce *would* skip (rate limits and dedup, replayed over the DB) and what aging *would* remove.
  The DB is opened mode=ro.
* Hook errors: in dry-run the write proceeds and a `hook_error` line is logged. With
  `enforce: true` a hook that cannot decide **denies** the write (fail closed).
* Turning enforce on is the operator's call. 2.1 does not turn it on.

## 5. RAG small judge
If the judge model cannot answer, the chunk is **excluded** (`fail_closed: true`). 2.0 included it.

## 6. Chamber / council
`AUTO_PROMOTE_RAG = False`. Council opinions never become live RAG memory without an approved
`chamber.promote` command.

## 7. Self-improvement loop (`nova/selfimprove.py`)
propose → council review (≥ 1 review, no `oppose`) → operator approve → apply **only into a folder
holding a `.nova_sandbox` marker** → verify (pytest) → `PROOF.json` (sha256 per file, tests rc,
reviewers, approver) + `master_log` line. Each stage refuses if the previous one is missing. There
is no auto-promote: moving a verified sandbox to the live kit is the manual cutover.

## 8. Staged-install guard
A kit with a `STAGED` marker file refuses `python -m nova` unless NOVA_HOME is one of the scratch
homes listed in `STAGED`. `nova.launch` and `START_NOVA.bat` refuse outright. `START_GUI.bat`
uses the scratch home.

## 9. Disk retention
`data/config/retention.json` holds the policy (stills: newest 200 or < 7 days; DB backups: keep 1;
`_play.wav` hash-identical duplicates; log rotation over 5 MB). `python -m nova.disk report` is a
**dry-run only**: 2.1 never deletes (`apply_enabled: false`). The daemon's old 2.0 `maintain`
TTS-wav purge is replaced by this report.
