from pathlib import Path
p = Path("nova/sched.py")
t = p.read_text(encoding="utf-8")
bad = 'if prompt and (P(prompt).exists() or "\\" in prompt or "/" in prompt):'
# actual broken line in file:
broken = 'if prompt and (P(prompt).exists() or "\\" in prompt or "/" in prompt):'
# Read raw line 147
lines = t.splitlines(True)
for i,l in enumerate(lines):
    if 'P(prompt).exists()' in l:
        print("LINE", i+1, repr(l))
        lines[i] = '            if prompt and (P(prompt).exists() or "\\\\" in prompt or "/" in prompt):\n'
        # wait - we want the source to contain: or "\\" in prompt
        lines[i] = '            if prompt and (P(prompt).exists() or "\\" in prompt or "/" in prompt):\n'
p.write_text(''.join(lines), encoding='utf-8')
# verify
import ast
ast.parse(p.read_text(encoding='utf-8'))
print('sched syntax OK')
for i,l in enumerate(p.read_text(encoding='utf-8').splitlines()):
    if 'P(prompt).exists()' in l:
        print('fixed', i+1, l)
