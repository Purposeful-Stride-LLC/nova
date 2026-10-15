# NOVA fieldkit 2.1 — Scheduler

The daemon (`python -m nova`) owns the scheduler. The TUI, the GUI and chat only **propose**; the
daemon executes. Code: `nova/sched.py`, `nova/gpulock.py`, `nova/cmdinbox.py`, `nova/taskstim.py`.

## Job table
`python -m nova.sched table` (or `/sched` in the TUI, or SYSTEM OPS in the GUI) shows:

| column | meaning |
|---|---|
| id | jobs-table id (use it in operator commands: `/job off 4`) |
| name | handler key (`holmes`, `cam:0`, `thermal-check`, `task-stimulus`, …) |
| cadence_s | `every_s` from the jobs table |
| priority | higher runs first within one tick |
| gpu | GPU class: `none`, `light` (≤ ~1 GB, e.g. qwen2:0.5b), `vision` (moondream), `heavy` (8B-class) |
| enabled | 1/0 |
| last run / next run | CT. `next run` = max(last run + cadence, backoff-until); "due now" when due |
| fails / last error | consecutive failures and the last error text |

Defaults live in `JOB_META` (sched.py). Override per job in `<NOVA_HOME>/data/config/scheduler.json`:
```json
{"jobs": {"nova-diary": {"priority": 30, "gpu": "light"}}, "backoff": {"base_s": 60, "max_s": 21600}}
```
State (last run, fails, backoff, run-now flags) is kept in `<NOVA_HOME>/data/run/sched_state.json`.
No DB schema change. After a restart, `next run` falls back to the jobs table `last_zulu`, so a
restart does not re-run every job at once.

## One tick
1. Execute **approved** commands from the inbox (each one logged to `master_log` as `cmd:<verb>`).
2. Collect due jobs, sort by priority.
3. Run them. A `heavy` or `vision` job takes the GPU lock first; **at most one exclusive GPU job per
   tick**. If another holder (the GUI chat, the TUI) has the lock, the job is *deferred* (`gpu_busy`)
   — not counted as a failure.
4. Record the result: success resets `fails`; an error sets `backoff_until = now + base·2^(fails-1)`,
   capped at `max_s` (default 60 s, 2 min, 4 min, … up to 6 h).

## GPU exclusivity
`gpulock` is a small JSON lock file under `data/run/`. It is shared by every process that uses the
same NOVA_HOME. Chat (`nova.chat.ask`) takes it with class `heavy` for the duration of one answer.
`gpulock.foreign_heavy(model)` reports a heavy model that is resident in Ollama but not ours (for
example another install's qwen3.5:9b). Chat reports it as *contention* rather than hiding it.
Chat default: **qwen3:8b, num_ctx 8192, think:false** (measured 6.19 GB, 100 % GPU).

## Command inbox (HIL)
Files under `<NOVA_HOME>/data/commands/{proposed,approved,done,denied}/`, moved atomically.

| verb | args | who may propose |
|---|---|---|
| job.pause / job.resume / job.run_now | id | operator, GUI, chat, task-stimulus |
| report.approve / report.close | id | operator, GUI, chat |
| url.approve / url.deny | id | operator, GUI, chat |
| url.enqueue, reports.approve_all, ingest.clear_standing, mail.deliver | see code | operator / GUI only |
| chamber.promote | case | chamber (2.1: proposal only) |
| selfimprove.apply | pid | operator |
| task.note | topic | task-stimulus (informational) |

* Chat proposals are limited by `gates.chat_scope` and always need an operator approve.
* A GUI click is an operator action: a confirm dialog, then `proposed→approved` in one step. The
  **daemon** performs the DB write on its next tick, so the GUI makes no DB writes.
* TUI: `/cmd list`, `/cmd approve ID`, `/cmd deny ID`.
* `url.approve` sets the queue row to `approved`, which is the **only** status `board.drain_one`
  drains. This closes the 2.0 gap where approve and drain looked at different statuses.

## Task stimulus (`task-stimulus`, every 600 s, priority 80, gpu none)
Reads (mode=ro): open HIL reports (grouped by title), URLs waiting for approval, pending docs,
failed packets, stale checks (enabled jobs not run within 3× cadence) and pending proposals.
It writes `data/run/task_now.json`. Up to 4 `TASK …` lines appear in the chat NOW block for 1 h.
It also proposes up to 3 next tasks (`job.run_now` for stale checks, `task.note` for report
triage). Duplicates are suppressed. **Nothing it proposes runs until the operator approves it.**
The daemon adds the job row (enabled) at start if it is missing.
