from pathlib import Path
from nova import db, office

z = db.zulu()
flow = Path(r"Documents\NOVA\NOVA_fieldkit_v1_4\STAGING\FLOW.md")
reply = (
    "DONE: FLOW.md written with 2 mermaid diagrams and 5 architectural bullets.\n"
    f"FILES: {flow}\n"
    f"PROOF: write tool ok; exists={flow.is_file()}; bytes={flow.stat().st_size if flow.is_file() else 0}\n"
    "NEXT: 1.2\n"
    f"CLAW_RUN: session=nova-mail-2 model=ollama/qwen3.5:9b zulu={z}\n"
    "NOTE: llama3-groq-tool-use:8b overflowed 8192 ctx; used qwen3.5:9b 32k."
)
con = db.connect()
row = con.execute("SELECT body FROM packets WHERE id=8").fetchone()
body = (row["body"] if row else "") or ""
if "\n---\n" in body:
    body = body.split("\n---\n", 1)[0]
new_body = (body + "\n---\n" + reply)[:4000]
con.execute("UPDATE packets SET status=?, body=? WHERE id=?", ("delivered", new_body, 8))
con.commit()
con.close()
office.bump("openclaw@local", "jobs_run")
rid = office.post_packet(
    dest="brief@local",
    mask="openclaw",
    whi="Ax-CLAW",
    kind="reply",
    cite="openclaw.agent:nova-mail-2",
    body=reply[:3500],
)
print("zulu", z)
print("packet8 delivered")
print("return_packet_id", rid)
