from pathlib import Path
p = Path("nova/leash.py")
t = p.read_text(encoding="utf-8")
t2 = t.replace('model: str = "ollama/qwen3.5:9b"', 'model: str = "ollama/qwen3.5:9b"')
# update driver_hint in openclaw_status
t2 = t2.replace(
    '"driver_hint": "ollama/llama3-groq-tool-use:8b"',
    '"driver_hint": "ollama/qwen3.5:9b (fallback: llama3-groq-tool-use:8b)"',
)
if t2 != t:
    p.write_text(t2, encoding="utf-8")
    print("leash hint updated")
else:
    print("leash check", "driver_hint" in t)
# Ensure openclaw_run default stays qwen3.5:9b
if 'model: str = "ollama/qwen3.5:9b"' in p.read_text(encoding="utf-8"):
    print("openclaw_run default ok")
