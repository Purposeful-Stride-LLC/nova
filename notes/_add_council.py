from pathlib import Path
p = Path("nova/chamber.py")
t = p.read_text(encoding="utf-8")
if "def council(" in t:
    print("council already")
else:
    add = '''

def council(topic: str, steward_report: str) -> dict:
    """Steward briefing -> round_robin MoE. Alias for round_robin with clear name."""
    return round_robin(topic, steward_report)
'''
    p.write_text(t.rstrip() + add + "\n", encoding="utf-8")
    print("added council()")
