# AI Code Testing Checklist (NOVA)

**Version:** 2026-09-20  
**Audience:** Any AI steward or coder (Grok Bot, OpenClaw/Claw, Qwen, humans)  
**Purpose:** Gate work in early, middle, and ship stages. Answer: does this code meet the definitions and conditions established for what it must contain and how it must function?

Companion report example: `STAGING/GROKBOT_FUNCTIONALITY_REPORT_2026-09-20.txt`  
Capability matrix: `STAGING/CAPABILITY_MATRIX_2026-09-20.txt`

---

## How to use (AI)

1. Read this file before writing or reviewing a STEP.
2. After a change, mark each applicable item **PASS / FAIL / N/A** with one line of evidence (path, command, count, sample address).
3. Prefer **BASIC STEPs**. Verify files on disk. Never claim DONE from model chat alone.
4. NOVA live kit is an overlay under `nova\`. **Never wipe** `data\NOVA.db`.
5. Claw writes under `C:\Users\wuchy\.openclaw\workspace\nova-out\` then steward pulls into the fieldkit.
6. Outbound email/DM requires human-in-the-loop (HIL) unless the user explicitly approved that send.
7. Promote durable lessons into `docs/advice/` and optionally palace facts / RAG chunks (see Advice stacking).

---

## Stage-agnostic questions (always ask)

- Does it run correctly on the **target machine** (here: TUF / Windows)?
- Is information at **each pipeline stage** formatted correctly (fields present, non-empty where required)?
- Are **WHI classifications** implemented as defined (wings vs library codes)?
- Does behavior match the **written definition and conditions** for this feature?
- Can another AI **reproduce the test** from this checklist and the evidence block alone?
- Did we **reuse** an existing animal/plugin (OpenClaw channel, ClawHub) when leaner than a rewrite?
- Are secrets out of git and out of RAG chunks?
- Is there a **rollback** or non-ship path (scrap module not wired to `__main__`)?
- Were prior STEPs **regressed** after this change?
- Would a steward sign this for ship?

---

## Stage 1 — Early (design / first cut)

Before substantial code:

- [ ] Acceptance criteria written (inputs, outputs, PASS definition)
- [ ] WHI plan: which `Ax-` / `Tx-` / `0x-` addresses; whether `1x*` hexclass belongs in `whi` or only in `cite`
- [ ] Pipeline stage named (raw → parser → Tx → report → HIL → Ax, or crawl → chunk, or chamber round)
- [ ] Risk class + HIL points named (especially send, delete, purge)
- [ ] Reuse vs rewrite decision recorded (prefer OpenClaw/ClawHub for messaging)
- [ ] Schema impact listed (new columns/tables; migration safe for existing DB)
- [ ] Logging / `breaklog` / diary stamp plan
- [ ] Test fixtures or sample URLs/paths named
- [ ] No secrets in repo paths; secrets only in agreed vault locations
- [ ] Target entrypoint named (`nova.gui.app`, TUI slash, sched job name) — scrap stays scrap

---

## Stage 2 — Middle (integration)

While building and wiring:

- [ ] Clean imports on target Python
- [ ] `python -m py_compile` on touched modules (and `__main__` path)
- [ ] One path exercised end-to-end on metal (not only unit imagination)
- [ ] Format contract: required fields non-empty (`whi`, `title`, `body` or documented exception)
- [ ] Facts/packets `whi` matches `^(Ax|Tx|0x)-` only (full table scan or sample≥200)
- [ ] Chunks `status` in `temp|live|cleared` only; promote/clear rules followed
- [ ] Sched job idempotent; `last_err` empty after smoke
- [ ] TUI slash and/or GUI tile wired if user-facing
- [ ] Leash/model timeouts and Unicode/Windows paths handled
- [ ] Claw artifacts appear under `nova-out` when Claw was the writer
- [ ] Rollback: feature flag or simply not flipping `__main__` to unbroken scrap

---

## Stage 3 — Late / before shipping

- [ ] Functionality report written (runtime table + WHI audit + stage format audit)
- [ ] Double-check: second pass or second seat (chamber/council) on risky cuts
- [ ] Regression: prior STEPs still PASS
- [ ] Performance fit for machine (avoid dual heavy LLM + cam spam on 16 GB)
- [ ] Docs/tutorial/FLOW updated for user-visible behavior
- [ ] Diary stamp in `GrokBot.log.ai` (local time + zulu)
- [ ] Lesson seeded to RAG / advice note if reusable
- [ ] HIL confirmed for any outbound email/DM
- [ ] Steward explicit ship yes — no silent flip of entrypoints
- [ ] Capability matrix updated if channels/apps changed

---

## NOVA-specific pipeline contracts

| Pipe | Contract |
|------|----------|
| Web ingest | URL → board/queue → matrix → `0x-WEB` or `Tx-REJECT` (+ reason in body) |
| Crawl | same-host fetch → chunk `status=temp` → classify/cite `crawl:1xNN:URL` → promote `live` → clear temp |
| Chamber | case id → seats → store temps → steward `Ax-CHAMBER` verdict → `clear_temps` |
| Claw leash | `handoff` packet → `openclaw_run` / `claw-run` → `Ax-CLAW` / fail stamp; files via `nova-out` |
| Cam | still → features → `Tx-CAM` (+ optional seer); do not auto-open video in-box |
| Wings vs library | `Ax`/`Tx`/`0x` = lifecycle wings on `facts.whi` / `packets.whi`; `1x*` hexclass = subject taxonomy (often in cite) |

**Never:** wipe `NOVA.db`; treat `deliver_inbox` (Ollama mask) as real Claw; ship `app_enhanced` while syntax/wiring broken; put API tokens in chunks.

---

## Evidence format (paste into reports)

```
ITEM: <checklist id or question>
RESULT: PASS | FAIL | N/A | PARTIAL
EVIDENCE: <command or query>
SAMPLE: <whi / path / count>
NOTES: <one line>
```

Example:

```
ITEM: facts.whi wing prefixes
RESULT: PASS
EVIDENCE: SELECT whi, COUNT(*) FROM facts GROUP BY whi; orphan scan = 0
SAMPLE: Ax-OLLAMA 723, 0x-WEB 116, Tx-CAM 126
NOTES: 1x* lives in chunk cite, not facts.whi
```

---

## Advice stacking (RAG / WHI)

High-quality notes help every AI that follows.

1. Write the lesson under `docs/advice/YYYY-MM-DD_short-slug.md` (one idea per file).
2. Optionally `put_fact` with `whi=0x-ADVICE` or `Ax-ADVICE`, title = slug, body = the note.
3. Optionally ingest as a **live** chunk with clear `source_cite=docs/advice/...` so `rag.search` can hit it.
4. Keywords in the first line: `advice testing whi checklist ship gate`.
5. Re-read this checklist + recent advice notes at the start of a long coding day.

### Seed topics worth stacking

- BASIC tool language for small models
- nova-out then steward pull
- WHI wings vs hexclass 1x*
- chamber council function use
- do not ship scrap GUI
- HIL before outbound send

---

## Quick ship gate (one screen)

Early criteria written? Middle compile+one E2E+WHI scan? Late report+regression+HIL+steward yes?  
If any FAIL on a ship-critical item → **do not ship**.

---

*End of AI_CODE_TESTING_CHECKLIST.md*
