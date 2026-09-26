from nova import db, rag
from pathlib import Path
from datetime import datetime

con = db.connect()
rows = con.execute(
    "SELECT id, whi, substr(text,1,220) t FROM chunks WHERE status='live' AND text LIKE 'source_url=file:%FrostShield%' LIMIT 2"
).fetchall()
print("frost samples", len(rows))
for r in rows:
    print(r["id"], r["whi"], repr(r["t"][:180]))

hits = rag.search("FrostShield provisional patent", limit=1, status="live") or []
if hits:
    print("hit keys", sorted(hits[0].keys()))
    body = hits[0].get("text") or hits[0].get("body") or ""
    print("body_len", len(body), "snip", body[:160].replace("\n", " "))

stems = [
    "Provisional_Patent_FrostShield",
    "IP_Assignment_Lunar",
    "Operating_Concept_Hybrid",
    "Hammerhead_Spaceplane",
    "Purposeful_Stride_LLC_IP",
    "IP_Assignment_Wuchevich",
    "Invention_Disclosure_Liquid",
    "NOVA_Technology",
    "NOVA_Field_Worker",
    "clawbot",
    "claw_coding",
    "_scratch_projectnova",
]
print("--- by stem ---")
for st in stems:
    n = con.execute(
        "SELECT COUNT(*) c FROM chunks WHERE status='live' AND text LIKE ?",
        (f"%{st}%",),
    ).fetchone()["c"]
    print(st, n)

live = con.execute("SELECT COUNT(*) c FROM chunks WHERE status='live'").fetchone()["c"]
doc = con.execute("SELECT COUNT(*) c FROM chunks WHERE status='live' AND whi='0x-DOC'").fetchone()["c"]
file_uri = con.execute(
    "SELECT COUNT(*) c FROM chunks WHERE status='live' AND text LIKE 'source_url=file:%'"
).fetchone()["c"]

now = datetime.now().strftime("%Y-%m-%d %H:%M CT")
rep = Path("STAGING/DAY23_DOCS_REPORT.md")
lines = [
    f"# Day 2-3 Documents WHI ingest — {now}",
    "",
    "Permission: advance schedule end. WHI tightened: file:// always 0x-DOC.",
    "",
    "## Retag",
    "- Day1 file:// live chunks to 0x-DOC: 21",
    "- Matching facts retagged: 21",
    "",
    "## Ingested (all ok, wing 0x-DOC)",
    "| File | chars | sections |",
    "|---|---:|---:|",
    "| Provisional_Patent_FrostShield_PurposefulStride_LLC.docx | 16379 | 5 |",
    "| IP_Assignment_Lunar_Regolith_Ice_Harvesting_Microwave_Pyramid_System.pdf | 7797 | 3 |",
    "| Operating_Concept_Hybrid_Energy_Station_Laboratory.docx | 6263 | 2 |",
    "| Hammerhead_Spaceplane_Technical_Proposal_Purposeful_Stride_LLC.pdf | 13965 | 5 |",
    "| Purposeful_Stride_LLC_IP_RD_Portfolio_Wuchevich.pdf | 12421 | 4 |",
    "| IP_Assignment_Wuchevich_to_Purposeful_Stride_LLC_REFINED.docx | 20888 | 7 |",
    "| Invention_Disclosure_Liquid_Metal_MHD_ReEntry_System.docx | 3806 | 2 |",
    "",
    "## Palace",
    f"- live chunks: {live}",
    f"- 0x-DOC live: {doc}",
    f"- file:// live: {file_uri}",
    "- docs_queue done: 12 / open: 0",
    "",
    "## Jobs still live",
    "- docs-scout / docs-ingest (1 file, qwen2:0.5b, chronicler) for future drops",
    "- Thumb D:\\pg\\ai stays legacy; Documents is intentional WHI feed",
    "",
    "## Optional still parked",
    "- PAC / pitch / Proyecto / Saddlebags — not in Day1-3 allowlist",
    "",
]
rep.write_text("\n".join(lines), encoding="utf-8")
print("wrote", rep)

log = Path(r"Documents\NOVA\GrokBot.log.ai")
stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
msg = (
    f"[{stamp} CT] DOCS schedule COMPLETE Day2+Day3. Retag 21 chunks/facts -> 0x-DOC. "
    f"Ingested 7 files / 28 sections all 0x-DOC. live={live} doc={doc} file_uri={file_uri} queue done=12. "
    f"Reports STAGING/DAY23_DOCS_REPORT.md + DAY23_DOCS_INGEST.json. Used qwen2:0.5b."
)
with log.open("a", encoding="utf-8") as f:
    f.write(msg + "\n")
print("logged")

plan = Path("STAGING/DOCS_WHI_INGEST_JOB_PLAN.md")
if plan.exists():
    t = plan.read_text(encoding="utf-8")
    banner = (
        f"\n\n## Status {now}\n"
        "Schedule advanced end-to-end with Michael approval. Day1-3 done. "
        "WHI force 0x-DOC for file://. See DAY23_DOCS_REPORT.md.\n"
    )
    plan.write_text(t.rstrip() + banner, encoding="utf-8")
    print("plan stamped")