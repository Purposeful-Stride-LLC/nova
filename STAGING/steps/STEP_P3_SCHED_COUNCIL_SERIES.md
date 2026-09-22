# STEP P3 — sched council-series (verify stub)
GOAL: Confirm sched.run_named('council-series') writes agenda only unless STEWARD_RUN=1.
DO: Manual tick or unit call; check STAGING/council_series/NEXT_TOPIC.json mtime/content.
DONE when: note contains agenda-only and no ollama load.
PROOF: file bytes of NEXT_TOPIC.json
OUT: STAGING/council_series/SMOKE_P3.txt
