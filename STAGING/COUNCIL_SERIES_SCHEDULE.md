# Council Series Schedule (GPU-polite, recursive)
Host: TUF America/Chicago · Locked: 2026-09-22 06:02 CDT
Style: match existing jobs (`thermal-check`, `ingest-drain`) — long intervals, thermal gate, small model.

## Rules (all seats)
1. **Default = agenda only.** Job `council-series` writes `STAGING/council_series/NEXT_TOPIC.json` + Ax-HOMESTEAD seed text. No LLM unless `STEWARD_RUN=1`.
2. **Thermal gate:** skip if GPU temp ≥ threshold (reuse thermal-check; if unknown, skip LLM).
3. **Model:** prefer `qwen2:0.5b` or CPU; never hold VRAM; `keep_alive=0`.
4. **Recursive:** council N+1 must open with prior council’s PROOF gaps from `STAGING/council_series/PROOF_GAPS.json`.
5. **Outputs:** JSON under `STAGING/council_series/` + fact-seed text for WHI ingest (`Ax-HOMESTEAD`).

## Series (A→I), one topic per slot

| Slot | Topic ID | Title | Suggested cron-like | every_s (sched) | Notes |
|------|----------|-------|---------------------|-----------------|-------|
| 0 | A | Beacon/tentacle always-on | Sun 06:00 CT weekly | 604800 | First to fire |
| 1 | B | Mail/job schema + waiting queue | Sun 07:00 CT | 604800 | After A PROOF |
| 2 | C | Education seed series | Tue 06:30 CT | 604800 | RAG population plan |
| 3 | D | WHI gap→search→ingest loop | Tue 07:30 CT | 604800 | Scheduled scout design |
| 4 | E | Leash Komodo→Claw forge | Thu 06:30 CT | 604800 | STAGING→live fold |
| 5 | F | Paper markets skeleton | Thu 07:30 CT | 604800 | No live trades |
| 6 | G | User-facing HIL/ear/diary/GUI | Sat 09:00 CT | 604800 | Client-of-DB only |
| 7 | H | GitHub sync cadence | Sat 10:00 CT | 604800 | Docs-only policy |
| 8 | I | Meta: recursive schedule health | Sat 11:00 CT | 604800 | Reviews A–H gaps |

## Register / sched notes
- Forge entry: `council-series` every_s=86400 (daily tick checks NEXT_TOPIC; does **not** run LLM).
- Optional steward enable: `council-series@live` only with STEWARD_RUN=1 env for one shot.
- Sibling jobs (existing style): `thermal-check` (~300s), `ingest` / drain (~600s), `mail` (~60–300s).
- Tentacle may receive verb=`council.agenda` (never `council.run` without steward).

## Output schema (per council)
```json
{
  "id": "council-A-2026-09-22",
  "topic": "A",
  "zulu": "2026-09-22T11:02:00Z",
  "model": "agenda-only|qwen2:0.5b",
  "thermal_ok": true,
  "opinions": [],
  "proof_required": ["tree", "sha256"],
  "proof_gaps_from_prior": [],
  "actions": ["STEP ids Claw may execute"],
  "ax_homestead_seed": "one paragraph fact text"
}
```

## Initial NEXT_TOPIC (bootstrap)
See `STAGING/council_series/NEXT_TOPIC.json` — topic A.
