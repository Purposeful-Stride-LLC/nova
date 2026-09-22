from pathlib import Path
import json, time
from nova import db, docs_ingest, thermal, homestead, novadiary, sched

# Register thermal-check + nova-diary jobs if missing
names = {r.get("name") for r in db.jobs()}
if "thermal-check" not in names:
    db.job_add("thermal-check", 600)  # every 10m
    print("added thermal-check")
if "nova-diary" not in names:
    db.job_add("nova-diary", 21600)  # every 6h
    print("added nova-diary")
# Speed docs-ingest a bit while cool: every 45m instead of 3h
for r in db.jobs():
    if r.get("name") == "docs-ingest" and int(r.get("every_s") or 0) > 3600:
        con = db.connect()
        con.execute("UPDATE jobs SET every_s=? WHERE id=?", (2700, r["id"]))
        con.commit()
        print("docs-ingest every_s -> 2700")
    if r.get("name") == "ingest-drain" and int(r.get("every_s") or 0) < 1200:
        pass

print("GATE", json.dumps(thermal.gate("llm"), default=str)[:400])

# Remaining docs: skip duplicate IP non-refined + duplicate NOVA -1
EXTRA = [
    Path(r"C:\Users\wuchy\Documents\Political_Action_Committee.pdf"),
    Path(r"C:\Users\wuchy\Documents\Saddlebags_with_Spurs_Concept_Paper.docx"),
    Path(r"C:\Users\wuchy\Documents\Proyecto_Bahia_Aguila_Pitch_Package.docx"),
]
# Optional: older IP assignment only if refined not enough — skip
docs_ingest.scout(EXTRA)
print("scouted extras")

results = []
for p in EXTRA:
    g = thermal.gate("llm")
    snap = g.get("snap") or {}
    print("pre", p.name, "band", snap.get("band"), "temp", (snap.get("gpu") or {}).get("temp_c"), "allow", g.get("allow"))
    if not g.get("allow"):
        results.append({"path": p.name, "ok": False, "error": "thermal_skip", "band": snap.get("band")})
        print("SKIP thermal", p.name)
        break
    r = docs_ingest.ingest_one(p, model="qwen2:0.5b", mask="chronicler", min_score=8)
    results.append({
        "path": p.name,
        "ok": r.get("ok"),
        "sections": r.get("sections"),
        "chars": r.get("chars"),
        "error": r.get("error"),
        "whis": list({x.get("whi") for x in (r.get("results") or []) if not x.get("skipped")}),
    })
    # polite cool-down between files
    time.sleep(8)
    g2 = thermal.snapshot()
    print("post", p.name, "temp", (g2.get("gpu") or {}).get("temp_c"), "band", g2.get("band"))

Path("STAGING/EXTRA_DOCS_INGEST.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print("INGEST", json.dumps(results, indent=2))

# Homestead cycle with thermal
cyc = homestead.cycle()
print("HOMESTEAD", json.dumps({"ok": cyc.get("ok"), "thermal": cyc.get("thermal"), "n_needs": len(cyc.get("needs") or [])}, indent=2))

# Diary — a few sweet tokens
diary = novadiary.write_entry(
    theme="palace filling — documents and cool metal",
    context=(
        "Michael asked to keep ingesting while temperature allows. "
        "Docs mind-palace advanced; thermal gate wired into homestead. "
        f"Just ingested: {[r['path'] for r in results if r.get('ok')]}. "
        f"Thermal band={(thermal.snapshot().get('band'))}."
    ),
)
print("DIARY", json.dumps({k: diary.get(k) for k in ("ok", "chars", "error", "preview", "path")}, indent=2))

con = db.connect()
print("live", con.execute("SELECT COUNT(*) c FROM chunks WHERE status='live'").fetchone()["c"])
print("doc", con.execute("SELECT COUNT(*) c FROM chunks WHERE status='live' AND whi='0x-DOC'").fetchone()["c"])
print("jobs", [(r.get("name"), r.get("every_s"), r.get("enabled")) for r in db.jobs()])

# update metal safety tree note
tree = Path("STAGING/METAL_SAFETY_MONITOR_TREE.md")
banner = """

## Thermal gate (wired 2026-09-21)

`nova/thermal.py` L0 snapshot + `gate(llm|speak)`:
- cool <65C, warm <75C, hot <82C, crit 88C
- VRAM free min 1200 MiB
- `docs-ingest` / `ingest-drain` skip when not llm_ok; cool allows limit=2 / 8
- `homestead-cycle` records Ax-THERMAL + need-thermal-cool when hot
- `office.snapshot_hw` embeds thermal blob
- Jobs: `thermal-check` @600s, `nova-diary` @21600s
"""
if "Thermal gate (wired" not in tree.read_text(encoding="utf-8"):
    tree.write_text(tree.read_text(encoding="utf-8").rstrip() + banner, encoding="utf-8")
    print("tree stamped")