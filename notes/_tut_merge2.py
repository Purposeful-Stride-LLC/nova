from pathlib import Path
p = Path("nova/tutorial.py")
text = p.read_text(encoding="utf-8")
if "PAGE 7  CLAW LEASH" in text:
    print("already")
else:
    lines = text.splitlines(keepends=True)
    idx = next(i for i,l in enumerate(lines) if l.strip()=="]")
    # add comma after last page
    for k in range(idx-1, -1, -1):
        if lines[k].strip():
            if lines[k].rstrip().endswith('"""') and not lines[k].rstrip().endswith(',"""'):
                if not lines[k].rstrip().endswith(','):
                    lines[k] = lines[k].rstrip('\r\n') + ",\n"
            break
    out = '''    """PAGE 7  CLAW LEASH
OpenClaw is a servant on 127.0.0.1:18789 — not the palace.
  /claw              status (TCP)
  /claw do the thing ask via HTTP if chatCompletions enabled
  /job add 120 claw-ping
  /job add 300 claw-run
Driver for tool STEPs: ollama/qwen3.5:9b (32k). lobster 8b overflows bootstrap.
Write path rule: Claw writes under ~/.openclaw/workspace/nova-out/ then NOVA pulls.
Never treat deliver_inbox as real Claw (that is Ollama mask mail).
""",
    """PAGE 8  MAIL + MEMORY SEEDS
leash.handoff -> packets -> openclaw_run/claw-run -> stamp delivered + brief@local reply.
Shared zulu clock. WHI: Ax- ok, Tx- break/task, 0x- web/artifact.
After leash gap-close: tighten RAG on facts/packets, then /web ingest into the memory palace.
""",
'''
    new = "".join(lines[:idx]) + out + "".join(lines[idx:])
    p.write_text(new, encoding="utf-8")
    print("added")
from nova import tutorial
print("n_pages check", tutorial.page(7)[:120].replace("\n"," | "))
print(tutorial.page(8)[:120].replace("\n"," | "))
