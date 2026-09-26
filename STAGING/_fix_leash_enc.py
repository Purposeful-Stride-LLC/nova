from pathlib import Path
p = Path("nova/leash.py")
t = p.read_text(encoding="utf-8")
old = "proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)"
new = "proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout + 30)"
if old in t:
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("fixed encoding")
elif "encoding='utf-8'" in t:
    print("already fixed")
else:
    print("needle missing")
