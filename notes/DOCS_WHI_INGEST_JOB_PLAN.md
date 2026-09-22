# Documents → WHI mind-palace ingest JOB PLAN
Status: PLAN — polite spaced ingest over next few days. Execute in slices, not one GPU binge.

## Doctrine (locked)
- **Thumb `D:\pg\ai`**: shared agent **legacy** — jack-in / homestead, do **not** melt into palace as primary knowledge.
- **`C:\Users\wuchy\Documents\`** (esp. Purposeful Stride / NOVA / FrostShield / IP papers + `Documents\NOVA\*.txt` notes): **intentional WHI feed** — orderly ingest + correct summation so local LLM RAG works when Nova wakes.

## Goal (next few days)
Mind palace correct: facts/chunks with real WHI prefixes, provenance headers, chronicler-quality summaries, live status — knowledge easy for `nova.rag` / chamber without micromanaging every drain.

## Pipeline (per document)
1. **Scout** — discover path, hash, bytes, mime
2. **Ingest raw** — pdf/docx/txt → temp chunk (hands.pdf / docx path / plain read)
3. **Matrix weigh** — score; reject junk below floor
4. **Summarize under mask** — chronicler (default) or analyst for technical IP; small model when GPU polite
5. **Promote live** — provenance header + WHI classify (`0x-DOC` / subject wing)
6. **Palace stamp** — fact Ax/0x + live chunk; optional chamber only if contested
7. **Index** — whi.ensure_indexes; RAG smoke query

## Job design (spaced / polite)
| Job | Cadence | Behavior |
|-----|---------|----------|
| `docs-scout` | 1×/day or manual | Walk Documents allowlist; enqueue new hashes to queue (http-less rows or docs queue table) |
| `docs-ingest` | every 2–4h, **limit 1–2 files** | One doc at a time through pipe; abort if free VRAM low or Aurelius busy |
| `docs-sum-drain` | with ingest-drain | Temps from docs cite → chronicler summary → live |
| midnight checksum | already on | Red if docs queue stuck / temps explode |

Polite rules: max 1 LLM summary concurrent; prefer qwen2:0.5b/qwen3:8b off-peak; no mega batch of 40; sleep between files.

## Allowlist (Documents — priority order for days 1–3)
### Day 1 — NOVA core narrative
- NOVA_Technology_Proposal_*.docx
- NOVA_Field_Worker_Platform_BPC_Concept_Spec_*.docx
- Documents\NOVA\clawbotinstructions.txt, claw_coding_playbook.txt, _scratch_projectnova_odt.txt

### Day 2 — FrostShield / lunar / energy
- Provisional_Patent_FrostShield_*.docx
- IP_Assignment_Lunar_Regolith_*.pdf
- Operating_Concept_Hybrid_Energy_Station_*.docx
- Hammerhead_Spaceplane_*.pdf (if space-settlement adjacent)

### Day 3 — IP portfolio / assignment / other concepts
- Purposeful_Stride_LLC_IP_RD_Portfolio_*.pdf
- IP_Assignment_Wuchevich_to_Purposeful_Stride_*.docx (refined preferred)
- Invention_Disclosure_Liquid_Metal_*.docx
- Saddlebags / Proyecto / PAC only if Michael marks in-scope (political/pitch may stay metadata-only)

## Correct format (summation contract)
Live chunk body starts with provenance block then clean summary:
source_path=...
accessed=zulu
llm=...
mask=chronicler|analyst
matrix_score=...
whi=0x-DOC|...
title=...

Then 1–3 short paragraphs + bullet key claims. Facts: short title, body ≤ palace contract. No raw 50-page dump as single chunk — **section split** long docx/pdf (hands already pattern for pdf).

## Success when Nova wakes
- RAG queries on NOVA / FrostShield / IP return live chunks with WHI + cites
- Settlement + Documents knowledge coexist without temp clog
- Thumb legacy still separate (homestead scan only)
- Jobs green on midnight checksum

## Out of scope this week
Melting entire thumb into RAG; live email/WA; paint; full viseme stitch.

## Execute gate
Approve Day-1 allowlist slice → implement `docs-scout` + `docs-ingest` (limit 1) → smoke one Technology Proposal → then Day 2–3.

## Inventory snapshot (2026-09-21 03:24 local)
- Hammerhead_Spaceplane_Technical_Proposal_Purposeful_Stride_LLC.pdf (17 KB)
- Invention_Disclosure_Liquid_Metal_MHD_ReEntry_System.docx (12 KB)
- IP_Assignment_Lunar_Regolith_Ice_Harvesting_Microwave_Pyramid_System.pdf (10 KB)
- IP_Assignment_Wuchevich_to_Purposeful_Stride_LLC.docx (17 KB)
- IP_Assignment_Wuchevich_to_Purposeful_Stride_LLC_REFINED.docx (19 KB)
- _scratch_projectnova_odt.txt (21 KB)
- claw_coding_playbook.txt (2 KB)
- clawbotinstructions.txt (10 KB)
- NOVA_Field_Worker_Platform_BPC_Concept_Spec_Purposeful_Stride_LLC.docx (17 KB)
- NOVA_Technology_Proposal_Purposeful_Strides_LLC_2026-08-06.docx (16 KB)
- NOVA_Technology_Proposal_Purposeful_Strides_LLC_2026-08-06-1.docx (16 KB)
- Operating_Concept_Hybrid_Energy_Station_Laboratory.docx (13 KB)
- Political_Action_Committee.pdf (326 KB)
- Provisional_Patent_FrostShield_PurposefulStride_LLC.docx (17 KB)
- Proyecto_Bahia_Aguila_Pitch_Package.docx (2 KB)
- Purposeful_Stride_LLC_IP_RD_Portfolio_Wuchevich.pdf (14 KB)
- Saddlebags_with_Spurs_Concept_Paper.docx (12 KB)

## Status 2026-09-21 04:00 CT
Schedule advanced end-to-end with Michael approval. Day1-3 done. WHI force 0x-DOC for file://. See DAY23_DOCS_REPORT.md.
