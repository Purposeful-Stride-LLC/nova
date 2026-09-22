from pathlib import Path
p = Path("nova/rag.py")
t = p.read_text(encoding="utf-8")
if "head.startswith(\"EXCLUDE\")" in t or "head.startswith('EXCLUDE')" in t:
    print("gate already tight")
else:
    old = 'include = text.upper().startswith("INCLUDE")'
    if old in t:
        t = t.replace(
            old,
            'head = (text.splitlines()[0].upper() if text else "")\n        include = head.startswith("INCLUDE")\n        if head.startswith("EXCLUDE"):\n            include = False',
            1,
        )
        p.write_text(t, encoding="utf-8")
        print("tightened")
    else:
        print("no simple startswith line", "INCLUDE" in t)
