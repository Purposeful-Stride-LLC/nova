# REPORT_CLAW_CHECKSUM_2026-09-26
Zulu: 2026-09-26T16:00:09Z
Author: Varro steward fallback (OpenClaw mail claimed writes but left disk empty; packets 430/432 proof-reject)

## Gateway
- Dashboard HTTP: 200
- openclaw gateway status (excerpt):
```
Service: Scheduled Task (registered)
File logs: ~\AppData\Local\Temp\openclaw\openclaw-2026-09-26.log
Command: C:\Program Files\nodejs\node.exe --max-old-space-size=8002 %APPDATA%\npm\node_modules\openclaw\dist\index.js gateway --port 18789
Service file: ~\.openclaw\gateway.cmd
Service env: OPENCLAW_GATEWAY_PORT=18789
Gateway heap: service argv: --max-old-space-size=8002; installer recommendation: 8002 MiB old space (16005 MiB physical capacity; adaptive cap 8192 MiB; native headroom cap 12003 MiB); runtime V8 ceiling: not measured
Host desktop: disabled

Config (cli): ~\.openclaw\openclaw.json
Config (service): ~\.openclaw\openclaw.json

Gateway: bind=loopback (127.0.0.1), port=18789 (service args)
Probe target: ws://127.0.0.1:18789
Dashboard: http://127.0.0.1:18789/
Probe note: Loopback-only gateway; only local clients can connect.

CLI version: 2026.9.4 (~\AppData\Roaming\npm\node_modules\openclaw\openclaw.mjs)
Gateway version: 2026.9.4

Runtime: running (pid 34548, last run 267009, last run time 2026-09-23T19:03:29.0000000Z, Gateway process detected for gateway port 18789.)
Connectivity probe: ok
Capability: read-only

Listening: 127.0.0.1:18789
Troubles: run openclaw status
Troubleshooting: https://docs.openclaw.ai/troubleshooting

```

## VRAM
- 8151 MiB, 6536 MiB, 1375 MiB
- free_mib=1375 (gate for paint is >=4096)

## Avatar residue
- avatar_display: True
- avatar_viseme: False
- report_build: True
- lipsync_steward: True
- lipsync_result: True

## Queue note
- Ignore stale `data/queue/waiting/council-avatar-viseme-20260922T115601Z.json`
- Dev-drop envelope present: job-fa9b2152-dc12-4b0a-9396-6b8b46e137d1.json

## Blockers
- OpenClaw agent turns acknowledged STEP but did not write files (PROOF reject correct).
- Paint PARKED: Ollama llama-server holds GPU.
