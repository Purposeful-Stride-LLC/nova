from pathlib import Path
p = Path("nova/tui/term.py")
t = p.read_text(encoding="utf-8")
if 'startswith("/claw")' in t:
    print("claw already wired")
else:
    needle = '    if low.startswith("/tts"):'
    block = '''    if low.startswith("/claw"):
        from nova import claw

        rest = raw[5:].strip()
        if not rest:
            return str(claw.status())[:800]
        return str(claw.ask(rest))[:1200]

''' + needle
    if needle not in t:
        raise SystemExit("tts needle missing")
    p.write_text(t.replace(needle, block, 1), encoding="utf-8")
    print("wired /claw")
