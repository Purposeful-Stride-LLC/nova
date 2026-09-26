# Optional paint wires (do not apply until unpark)

## 1. TUI `/paint` (mirror `/qwen`)

In `nova/tui/term.py`, before `/claw`:

```python
    if low.startswith("/paint"):
        from nova.hands import paint as paint_hand
        rest = raw[6:].strip()
        if not rest:
            return "usage: /paint PROMPT   | /paint status"
        if rest.lower() == "status":
            import json
            return json.dumps(paint_hand.status(), indent=2)[:1200]
        return str(paint_hand.generate(rest))[:1200]
```

## 2. Do not

- Wire paint into avatar mood selection
- `ollama pull` anything named qwen-image
- Auto-start ComfyUI from sched without thermal gate