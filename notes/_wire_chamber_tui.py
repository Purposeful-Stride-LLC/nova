from pathlib import Path
p = Path("nova/tui/term.py")
t = p.read_text(encoding="utf-8")
if 'startswith("/chamber")' in t:
    print("/chamber already")
else:
    needle = '    if low.startswith("/snap"):'
    block = '''    if low.startswith("/chamber"):
        from nova import chamber
        import json

        rest = raw[8:].strip()
        if rest.startswith("clear "):
            return str(chamber.clear_temps(rest[6:].strip()))
        if rest.startswith("list "):
            return str(chamber.list_temps(rest[5:].strip()))[:800]
        return "usage: /chamber list CASE | /chamber clear CASE"

'''
    if needle not in t:
        needle = '    if low.startswith("/claw"):'
    t = t.replace(needle, block + needle, 1)
    p.write_text(t, encoding="utf-8")
    print("wired /chamber")
