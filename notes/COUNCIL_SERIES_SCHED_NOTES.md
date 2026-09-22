# Council series — sched registration notes
Updated: 2026-09-22 06:02 CDT

## Job name
`council-series` — disabled by default on live DB; forge suggests every_s=86400.

## Behavior (coded stub)
- Always: refresh/advance NEXT_TOPIC file under STAGING/council_series/ when cool.
- LLM/chamber: only if env STEWARD_RUN=1 and thermal gate passes.
- Prefer writing agenda JSON + Ax-HOMESTEAD seed text; never thrash GPU.

## Enable (steward)
1. Confirm thermal-check healthy.
2. `STEWARD_RUN=1` for one daemon tick OR TUI job enable with long every_s.
3. First topic: A (beacon always-on).
