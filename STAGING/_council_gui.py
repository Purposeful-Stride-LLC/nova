"""Council round: steward report on Claw GUI overnight + codebase next step."""
from __future__ import annotations
import json
from pathlib import Path
from nova import chamber, db

REPORT = """
STEWARD GROK BOT CODEBASE / GUI GRADE (2026-09-20)

FACTS:
- Live GUI entry: nova/gui/__main__.py -> nova.gui.app.main (app.py ~11KB). Works as cosmic console + deck.json.
- Claw overnight wrote nova/gui/app_enhanced.py (~26KB) + STAGING/claw_report_gui_enhancements.txt.
- app_enhanced.py does NOT run: SyntaxError line ~395 self.addWidget(QFrame())).
- Enhanced not wired: deck buttons connect to None; chat not hooked to nova.tui.term.handle();
  QueueTracker subclasses QVBoxLayout (wrong); no main()/entry; brand path parents[3] suspect.
- Helpers: drain_queue.py, list_tables.py, report_db_contents.py (useful but blunt).
- nova-out/rag_gate_notes.md present. sched.py had broken qwen: path string (steward fixed).
- Palace has crawl/RAG/chamber/leash already; PAPER MARKETS tile dead + STAGING/PAPER_MARKETS.md.

STEWARD LEAN:
Prefer porting Priority-1 (palace QTableWidget + search) into live app.py over flipping __main__ to enhanced.
Keep Claw BASIC STEPs -> nova-out -> steward pull.

QUESTION FOR COUNCIL (each seat, max 12 lines):
1) Agree or disagree with steward lean? Why?
2) Top 3 concrete next coding STEPs (ordered) for Claw or Qwen.
3) One risk if we ship enhanced as-is.
4) Should paper markets wait until GUI Priority-1 lands?
"""

print("council start", db.zulu(), flush=True)
out = chamber.round_robin("gui-codebase-grade-2026-09-20", REPORT)
print(json.dumps(out, indent=2)[:3500], flush=True)

# Pull full opinions
case = out["case"]
con = db.connect()
opinions = {}
for seat in ("claw", "qwen", "code"):
    title = f"chamber/{case}/{seat}"
    row = con.execute("SELECT body FROM facts WHERE whi='Tx-TEMP' AND title=?", (title,)).fetchone()
    if row:
        opinions[seat] = json.loads(row["body"]).get("opinion", "")
    print("====", seat, "====", flush=True)
    print((opinions.get(seat) or "")[:1500], flush=True)

Path("STAGING/COUNCIL_GUI_GRADE.json").write_text(
    json.dumps({"case": case, "round": out, "opinions": opinions}, indent=2),
    encoding="utf-8",
)
print("wrote STAGING/COUNCIL_GUI_GRADE.json", flush=True)
