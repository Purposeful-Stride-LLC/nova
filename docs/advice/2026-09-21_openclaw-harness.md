# advice OpenClaw harness for NOVA (2026-09-21)
- Real Claw path: palace handoff → leash.openclaw_run / sched claw-run (NOT deliver_inbox Ollama mask).
- Model: ollama/qwen3.5:9b for tool STEPs; lobster 8b overflows full bootstrap.
- Write only to ~/.openclaw/workspace/nova-out/; steward pulls to fieldkit.
- BASIC tool language STEPs; verify bytes on disk.
- Feedback counters employees.accepted/rejected/agree/dissent exist but are NOT wired (all 0) — report cards / HIL ack should increment.
- Browser plugin enabled; HIL playbook in nova-out.
