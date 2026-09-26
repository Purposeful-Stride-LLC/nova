from pathlib import Path
p = Path("nova/tutorial.py")
t = p.read_text(encoding="utf-8")
if "/qwen" in t and "PAGE 7" in t and "qwen --prompt" in t:
    print("tutorial qwen already")
elif "PAGE 7  CLAW LEASH" in t and "/qwen PROMPT" not in t:
    t = t.replace(
        "  /job add 300 claw-run\n",
        "  /job add 300 claw-run\n  /qwen PROMPT       qwen --prompt subprocess valet\n  /job add 600 qwen:Say pong\n",
        1,
    )
    p.write_text(t, encoding="utf-8")
    print("tutorial page7 qwen lines added")
else:
    print("skip tutorial", "/qwen" in t)
