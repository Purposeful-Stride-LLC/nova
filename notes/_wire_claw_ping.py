from pathlib import Path
p = Path("nova/sched.py")
t = p.read_text(encoding="utf-8")
if 'key == "claw-ping"' in t:
    print("claw-ping present")
else:
    needle = '        elif key == "claw-run":'
    block = '''        elif key == "claw-ping":
            from nova import claw

            note = str(claw.status())[:200]
''' + needle
    if needle not in t:
        # try after openclaw-status
        needle = '        elif key == "openclaw-status":'
        block = '''        elif key == "claw-ping":
            from nova import claw

            note = str(claw.status())[:200]
''' + needle
    if needle not in t:
        raise SystemExit("sched needle missing")
    p.write_text(t.replace(needle, block, 1), encoding="utf-8")
    print("wired claw-ping")
