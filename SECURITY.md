# Security model — NOVA Fieldkit v2.1

NOVA is built to fail closed. If a gate cannot decide, it refuses.

## Gate model

- **Fail-closed.** Missing or malformed config falls back to safe defaults: no network hosts, chat proposals need an ack, the governor only logs. The RAG judge excludes on error.
- **Allowlist.** `/web`, crawl, board drain and docs-scout only reach hosts listed in `data/config/gates.json` → `net_allowlist`. The shipped example (`config.example/gates.json`) is **empty**, so all web access is refused until the operator adds hosts. Refusals are logged to `data/gates/gates.jsonl`.
- **HIL approvals.** Chat, GUI and the `task-stimulus` job can only *propose* commands into the inbox. Nothing runs until the operator approves (`/cmd approve ID`); the daemon executes approved items on its next tick. Outbound mail, mic and messaging bridges are also approval-gated. The self-improve loop is HIL-only with PROOF before DONE.
- **Read-only GUI.** The GUI opens the database `mode=ro` and never writes; its buttons file proposals.
- **No LLM-commanded actions.** Model output is text. It cannot execute tools, change jobs or reach the network by itself; parsers ignore action claims, and chat verbs are limited to `chat_scope`.
- **Governor.** `enforce` defaults to `false` (dry-run). Destructive maintenance refuses unless an operator sets `enforce: true`.
- **Disk.** Retention is report-only in v2.1.

## Secrets

Never commit `.env`, API keys, tokens, SSH keys, `data/` or `*.db`. Keys are read from environment variables or `data/secrets/` (gitignored).

## Reporting a vulnerability

Please do not post vulnerability details in a public issue. Instead, [open an issue](https://github.com/Purposeful-Stride-LLC/nova/issues/new) titled "Security contact request" that contains **no technical details**, and a maintainer from Purposeful Stride LLC will reply with a private channel. When reporting privately, include steps to reproduce and the version (`VERSION`).
