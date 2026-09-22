from pathlib import Path
p = Path("nova/tutorial.py")
t = p.read_text(encoding="utf-8")
if "PAGE 7  CLAW LEASH" in t:
    print("tutorial already has page 7")
else:
    extra = '''    """PAGE 7  CLAW LEASH
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
    # insert before closing bracket of PAGES
    needle = "]\n\n\ndef page"
    if needle not in t:
        needle = "]\r\n\r\n\r\ndef page"
    if "]\n\ndef page" in t:
        t = t.replace("]\n\ndef page", ",\n" + extra + "]\n\ndef page", 1)
    elif "]\r\n\r\ndef page" in t:
        t = t.replace("]\r\n\r\ndef page", ",\r\n" + extra + "]\r\n\r\ndef page", 1)
    else:
        # find last """ before ]
        idx = t.rfind("\",\n]")
        if idx < 0:
            idx = t.rfind('""",\n]')
        raise SystemExit("cannot find PAGES end: " + repr(t[t.find("PAGES"):t.find("PAGES")+80]))
    p.write_text(t, encoding="utf-8")
    print("added pages 7-8")
print(Path("nova/tutorial.py").read_text(encoding="utf-8")[-800:])
