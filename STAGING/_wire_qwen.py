from pathlib import Path

# TUI
p = Path("nova/tui/term.py")
t = p.read_text(encoding="utf-8")
if 'startswith("/qwen")' in t:
    print("tui /qwen already")
else:
    needle = '    if low.startswith("/claw"):'
    block = '''    if low.startswith("/qwen"):
        from nova.hands import qwen as qwen_hand

        rest = raw[5:].strip()
        if not rest:
            return "usage: /qwen PROMPT"
        return str(qwen_hand.run_prompt(rest))[:1200]

'''
    if needle in t:
        t = t.replace(needle, block + needle, 1)
        p.write_text(t, encoding="utf-8")
        print("wired /qwen before /claw")
    else:
        needle2 = '    if low.startswith("/tts"):'
        if needle2 not in t:
            raise SystemExit("no insert point")
        t = t.replace(needle2, block + needle2, 1)
        p.write_text(t, encoding="utf-8")
        print("wired /qwen before /tts")

# sched qwen:
p = Path("nova/sched.py")
t = p.read_text(encoding="utf-8")
if 'startswith("qwen:")' in t:
    print("sched qwen: already")
else:
    needle = '        elif key == "qwen-status":'
    block = '''        elif key.startswith("qwen:"):
            from nova.hands import qwen as qwen_hand

            prompt = key.split(":", 1)[1].strip() or "Say pong"
            # If looks like a path, ask qwen to summarize that path
            from pathlib import Path as P
            if prompt and (P(prompt).exists() or "\\" in prompt or "/" in prompt):
                prompt = f"List or summarize paths only, no writes: {prompt}"
            note = str(qwen_hand.run_prompt(prompt, timeout=180))[:200]
'''
    if needle not in t:
        raise SystemExit("qwen-status needle missing")
    p.write_text(t.replace(needle, block + needle, 1), encoding="utf-8")
    print("wired qwen: job")
