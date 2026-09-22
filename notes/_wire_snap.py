from pathlib import Path
p = Path("nova/tui/term.py")
t = p.read_text(encoding="utf-8")
if 'startswith("/snap")' in t:
    print("/snap already")
else:
    needle = '    if low.startswith("/qwen"):'
    block = '''    if low.startswith("/snap"):
        from nova import snap as snapmod

        rest = raw[5:].strip()
        return str(snapmod.snap(rest or "tui snap"))[:400]

'''
    if needle not in t:
        needle = '    if low.startswith("/claw"):'
        block = '''    if low.startswith("/snap"):
        from nova import snap as snapmod

        rest = raw[5:].strip()
        return str(snapmod.snap(rest or "tui snap"))[:400]

'''
    t = t.replace(needle, block + needle, 1)
    p.write_text(t, encoding="utf-8")
    print("wired /snap")
