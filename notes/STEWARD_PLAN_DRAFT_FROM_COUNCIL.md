# STEWARD PLAN DRAFT — from Roberts council 2026-09-21
Session: 20260921T0100-50c71291
Seats: small (qwen2:0.5b) → code (codellama) → claw (qwen3.5:9b). Qwen design seat OFF.
Claw mail smoke: packet 60 OK — "Confirmed. Tool: web_fetch. Ready for input."
Status: DRAFT for human approval. No OpenClaw build STEPs execute until you approve.

## How to read the room
- **small**: terse Agree — useful as a go/no-go ping, thin on detail.
- **code**: often confused briefs (misread voice names; opposed visible daemon windows). Weight lower on product ops.
- **claw**: most actionable (Agree/Amend + concrete next cuts). Primary implementer seat.

## Motion outcomes (steward judgment)

### M1 Voice / TTS / parser / grammar — CARRY (Amend)
Consensus lean: fix speak path; change default voice off Alba.
- Pin SERVE_BASE :8000 (already); diagnose peel→speak when serve up but silent.
- Default NOVA/brief voice → **anna** (not eve; code wrongly flipped names — Alba is current mannish complaint).
- Tighten parser.GRAMMAR + masks system text: one [speak seat] pattern, female seat map (brief=anna).
**OpenClaw STEP later:** optional — mostly steward/Python spine.

### M2 Startup titled windows — CARRY (Agree, claw)
Visible titled consoles for daemon + TTS, then GUI; batch start, no long idle gap.
Code opposed always-visible (prefer menu) — steward overrides: user explicitly cannot see windows.
**OpenClaw STEP:** none required; steward launch/START_*.bat.

### M3 GUI chrome — CARRY (Agree all)
QScrollArea / resize on live app.py; wire deck→panels; do not ship app_enhanced; archive enhanced to STAGING.
**OpenClaw STEP:** optional BASIC patch into nova-out for scroll helper — or steward ports directly.

### M4 Mail / tools / browser — CARRY (Agree claw+small; code dissent misread)
Mail path proven this session. Browser plugin already enabled; supervised HIL smoke next (no auto-click).
**OpenClaw STEPs:** (1) browser status/capabilities note to nova-out (2) one HIL public-URL open after approve.

### M5 Vision metadata — CARRY (Agree; amend schema-first)
Schema cam_metadata before VLM; cam0 still + JSON meta; dynamic cams no fake geo; HIL before promote.
**OpenClaw STEP:** draft schema + cam0 capture stub → nova-out only.

### M6 Claw GUI methodology — CARRY (Agree live-port doctrine)
Keep Priority-1 into live app.py; quarantine enhanced; do not flip __main__.
**OpenClaw STEP:** none for rewrite; methodology lock for future GUI STEPs.

## Recommended implementation order (after your approve)

| # | Owner | Work |
|---|--------|------|
| 1 | Steward | Fix peel→speak smoke; set brief/NOVA default voice **anna**; update GRAMMAR seat map |
| 2 | Steward | START_NOVA: titled TTS :8000 + titled daemon + GUI (visible) |
| 3 | Steward | GUI: QScrollArea + resizable; deck smoke; leave enhanced scrap |
| 4 | Claw mail | BASIC: write browser HIL playbook to nova-out (no clicks yet) |
| 5 | Claw mail | BASIC: cam_metadata schema + cam0 still stub → nova-out |
| 6 | Steward | HIL browser smoke (you present) once playbook exists |
| 7 | Later | PoE multi-stream / WhatsApp QR / email plugin |

## Format test verdict
Council-first → steward plan → your approve → Claw STEPs: **worthy**. Mail+tool smoke passed. Small seat is a cheap thermometer; claw is the workhorse; code needs shorter BASIC prompts next time.

## Awaiting
Your approve / amend of this plan. Nothing further mailed for build until then.
