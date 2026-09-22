
import json
from pathlib import Path
from nova import chamber, leash, db

ST = Path("STAGING")
ST.mkdir(exist_ok=True)

MOTIONS = [
  {"id": "M1", "title": "Voice / TTS / parser / system-prompt grammar",
   "problem": "SUB: Pocket TTS :8000 (not CORS :3000). Serve up but speech silent — parser.peel / [speak] / term GRAMMAR.\\nSUB: Alba too mannish; prefer anna or eve.\\nSUB: System prompt must teach any LLM parseable speak/tool cues.\\nAsk: Agree/Amend/Oppose on pin :8000, fix peel->speak, default voice anna, tighten GRAMMAR. Risk. Next cut."},
  {"id": "M2", "title": "Startup: titled daemon + TTS windows then GUI",
   "problem": "SUB: User cannot see daemon/TTS windows. Need titled consoles.\\nSUB: START_NOVA: TTS :8000, daemon, then GUI; NOVA_FAST splash.\\nAsk: Agree/Amend/Oppose always-visible spawn titles. Risk. Next cut."},
  {"id": "M3", "title": "GUI chrome: resize, scroll, buttons, palace table",
   "problem": "SUB: Window too large; no scroll when small.\\nSUB: Deck buttons -> correct panels. Palace QTableWidget live in app.py.\\nSUB: Do NOT ship app_enhanced.\\nAsk: Agree/Amend/Oppose Priority-1 scroll/resize in live app.py. Risk. Next cut."},
  {"id": "M4", "title": "Mail leash / Claw tool-calling / browser plugin",
   "problem": "SUB: Mail openclaw@local as NOVA; openclaw_run BASIC tool smoke.\\nSUB: browser-plugin enabled — identify page/click with HIL.\\nAsk: Agree/Amend/Oppose mail-first then supervised browser smoke. Risk. Next cut."},
  {"id": "M5", "title": "Vision OpenCV cam metadata toward PoE",
   "problem": "SUB: cam0 still -> Tx-CAM + metadata cam_id, fixed|dynamic, location?, orientation?, zulu; VLM HIL.\\nSUB: Later PoE streams; dynamic cams no geoloc.\\nAsk: Agree/Amend/Oppose schema-first then cam0 STEP. Risk. Next cut."},
  {"id": "M6", "title": "SEPARATE: Claw GUI methodology vs live Priority-1 port",
   "problem": "Viewpoints only. Enhanced scrap vs port into live app.py.\\nAsk: Keep live-port doctrine? Agree/Amend/Oppose. Risk. Next cut."},
]

(ST / "COUNCIL_AGENDA_2026-09-20.json").write_text(
    json.dumps({"motions": MOTIONS, "seats": ["small", "code", "claw"], "qwen_design": "off"}, indent=2),
    encoding="utf-8")
print("agenda ok", flush=True)

body = "FROM NOVA palace. KIND council-task. BASIC STEP. 1) Confirm receipt. 2) Name one tool (status or browser). 3) No writes outside nova-out. Under 15 lines."
pid = leash.handoff("openclaw@local", "council-task", body, whi="Tx-CLAW")
print("handoff", pid, flush=True)
run = leash.openclaw_run(
    "You are Claw under NOVA palace mail. BASIC STEP. 1) Confirm receipt. 2) List one tool (browser or status). 3) No writes outside nova-out. Under 15 lines.",
    session_id="nova-council-mail",
    model="ollama/qwen3.5:9b",
    timeout=150,
    packet_id=pid,
)
smoke = {"packet_id": pid, "ok": run.get("ok"), "zulu": db.zulu(), "text_head": (run.get("text") or run.get("error") or "")[:2000]}
(ST / "COUNCIL_CLAW_MAIL_SMOKE.json").write_text(json.dumps(smoke, indent=2, ensure_ascii=False), encoding="utf-8")
print("smoke", smoke["ok"], smoke["text_head"][:180], flush=True)

print("session start", flush=True)
result = chamber.session_motions(MOTIONS, seats=("small", "code", "claw"))
(ST / "COUNCIL_ROBERTS_2026-09-20.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print("session done", result.get("session"), "n", len(result.get("motions") or []), flush=True)
for m in result.get("motions") or []:
    c = m.get("case")
    if c:
        print("clear", c, chamber.clear_temps(c), flush=True)
print("ALL_DONE", flush=True)
