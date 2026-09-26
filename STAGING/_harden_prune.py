from pathlib import Path
import re

# --- db.put_fact harden ---
p = Path("nova/db.py")
t = p.read_text(encoding="utf-8")
if "Format contract:" not in t:
    if "import re" not in t.split("def put_fact")[0]:
        if "from __future__ import annotations" in t:
            t = t.replace(
                "from __future__ import annotations\n",
                "from __future__ import annotations\n\nimport re\n",
                1,
            )
        else:
            t = "import re\n" + t
    old = '''def put_fact(whi: str, title: str, body: str, **meta) -> None:
    con = connect()
    con.execute(
        "INSERT INTO facts(zulu, whi, title, body) VALUES (?,?,?,?)",
        (zulu(), whi, title[:160], (body or "")[:8000]),
    )
    con.commit()
    con.close()'''
    new = '''def put_fact(whi: str, title: str, body: str, **meta) -> None:
    """Format contract: wing whi Ax-|Tx-|0x-; non-empty title; body preferred."""
    w = (whi or "").strip()
    if not (w.startswith("Ax-") or w.startswith("Tx-") or w.startswith("0x-")):
        raise ValueError(f"whi must be Ax-|Tx-|0x- wing, got {w!r}")
    title = re.sub(r"\\s+", " ", (title or "").strip())
    if not title:
        title = meta.get("fallback_title") or w
    body = body if body is not None else ""
    if not str(body).strip():
        reason = meta.get("reason") or meta.get("label") or "empty-body"
        body = f"reason={reason}"
        if meta.get("source_url"):
            body += f"\\nurl={meta['source_url']}"
    con = connect()
    con.execute(
        "INSERT INTO facts(zulu, whi, title, body) VALUES (?,?,?,?)",
        (zulu(), w, title[:160], str(body)[:8000]),
    )
    con.commit()
    con.close()'''
    if old not in t:
        raise SystemExit("db.put_fact OLD mismatch")
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")
    print("db.put_fact hardened")
else:
    print("db.put_fact already")

# --- matrix page_title ---
mp = Path("nova/matrix.py")
mt = mp.read_text(encoding="utf-8")
if "def page_title" not in mt:
    mp.write_text(
        mt.rstrip()
        + '''

def page_title(raw: str) -> str:
    """HTML <title> only, cleaned; empty if missing."""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw or "")
    if not m:
        return ""
    t = re.sub(r"\\s+", " ", m.group(1)).strip()
    t = re.split(r"\\s*[|\\u2013\\u2014]\\s*Contents", t)[0].strip()
    return t[:160]
''',
        encoding="utf-8",
    )
    print("matrix.page_title added")
else:
    print("matrix.page_title exists")

# --- web.py ---
wp = Path("nova/hands/web.py")
wt = wp.read_text(encoding="utf-8")
wt = wt.replace(
    "from nova.matrix import analyze, dump, strip_html",
    "from nova.matrix import analyze, dump, strip_html, page_title",
)
if "reason={matrix" in wt:
    print("web already")
else:
    old_web = '''    html = raw.decode("utf-8", "replace")
    text = strip_html(html)
    matrix = analyze(text, html_len=len(html))
    dest = db.home() / "data" / "artifacts" / "web_last.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"{final}\\n{dump(matrix)}\\n\\n{text[:20000]}", encoding="utf-8")
    if matrix["label"] != "ingest":
        db.put_fact(
            "Tx-REJECT",
            matrix["label"],
            text[:1500],
            source_url=final,
            content_hash=matrix["hash"],
            matrix_json=dump(matrix),
        )
        return {"ok": True, "ingested": False, "url": final, "matrix": matrix, "path": str(dest)}
    title = " ".join(w for w, _ in matrix.get("top") or [])[:80] or final
    db.put_fact(
        "0x-WEB",
        title,
        text[:8000],
        source_url=final,
        content_hash=matrix["hash"],
        matrix_json=dump(matrix),
    )'''
    new_web = '''    html = raw.decode("utf-8", "replace")
    title = page_title(html) or final
    text = strip_html(html)
    matrix = analyze(text, html_len=len(html))
    dest = db.home() / "data" / "artifacts" / "web_last.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"{final}\\n{dump(matrix)}\\n\\n{text[:20000]}", encoding="utf-8")
    if matrix["label"] != "ingest":
        reject_body = (
            f"reason={matrix['label']}\\nurl={final}\\nscore={matrix.get('score')}\\n"
            f"chars={matrix.get('chars')}\\n\\n{(text or '')[:1200]}"
        )
        db.put_fact(
            "Tx-REJECT",
            f"{matrix['label']}:{title}"[:160],
            reject_body,
            source_url=final,
            content_hash=matrix["hash"],
            matrix_json=dump(matrix),
            reason=matrix["label"],
        )
        return {"ok": True, "ingested": False, "url": final, "matrix": matrix, "path": str(dest), "title": title}
    db.put_fact(
        "0x-WEB",
        title[:160],
        f"url={final}\\n\\n{text[:7800]}",
        source_url=final,
        content_hash=matrix["hash"],
        matrix_json=dump(matrix),
    )'''
    if old_web not in wt:
        raise SystemExit("web OLD mismatch")
    wp.write_text(wt.replace(old_web, new_web), encoding="utf-8")
    print("web hardened")

# --- crawl ---
cp = Path("nova/crawl.py")
ct = cp.read_text(encoding="utf-8")
if "fallback_title=" not in ct:
    old_ing = '''def ingest_temp(url: str, text: str, title: str, depth: int) -> int:
    con = db.connect(); _ensure(con)
    body = f"title={title}\\ndepth={depth}\\nurl={url}\\n\\n{text}"[:8000]
    hx = hashlib.sha256(body.encode()).hexdigest()[:16]
    code = classify(text, url)
    con.execute(
        "INSERT INTO chunks(zulu,whi,source_cite,text,hash,status) VALUES (?,?,?,?,?,?)",
        (db.zulu(), "Tx-TEMP", f"crawl:{code}:{url}", body, hx, "temp"),
    )
    con.commit(); cid = int(con.execute("SELECT last_insert_rowid()").fetchone()[0]); con.close()
    db.put_fact("Tx-TEMP", f"crawl/{hx}", body[:4000])
    return cid'''
    new_ing = '''def ingest_temp(url: str, text: str, title: str, depth: int) -> int:
    con = db.connect(); _ensure(con)
    title = (title or "").strip() or url
    body = f"title={title}\\ndepth={depth}\\nurl={url}\\n\\n{text}"[:8000]
    hx = hashlib.sha256(body.encode()).hexdigest()[:16]
    code = classify(text, url)
    con.execute(
        "INSERT INTO chunks(zulu,whi,source_cite,text,hash,status) VALUES (?,?,?,?,?,?)",
        (db.zulu(), "Tx-TEMP", f"crawl:{code}:{url}", body, hx, "temp"),
    )
    con.commit(); cid = int(con.execute("SELECT last_insert_rowid()").fetchone()[0]); con.close()
    db.put_fact("Tx-TEMP", title[:160], body[:4000], fallback_title=f"crawl/{hx}")
    return cid'''
    if old_ing not in ct:
        raise SystemExit("crawl ingest OLD mismatch")
    ct = ct.replace(old_ing, new_ing)
    print("crawl ingest hardened")
else:
    print("crawl ingest already")

if "all_temp: bool" not in ct:
    old_clear = '''def clear_temp_chunks(older_than_zulu: str | None = None) -> int:
    con = db.connect(); _ensure(con)
    if older_than_zulu:
        n = con.execute("UPDATE chunks SET status='cleared' WHERE status='temp' AND zulu<?", (older_than_zulu,)).rowcount
    else:
        n = 0  # require explicit zulu or use chamber.clear_temps for opinions
    con.commit(); con.close(); return int(n or 0)'''
    new_clear = '''def clear_temp_chunks(older_than_zulu: str | None = None, all_temp: bool = False) -> int:
    """Clear crawl temp chunks. all_temp=True clears every status=temp (steward prune)."""
    con = db.connect(); _ensure(con)
    if all_temp:
        n = con.execute("UPDATE chunks SET status='cleared' WHERE status='temp'").rowcount
    elif older_than_zulu:
        n = con.execute("UPDATE chunks SET status='cleared' WHERE status='temp' AND zulu<?", (older_than_zulu,)).rowcount
    else:
        n = 0
    con.commit(); con.close(); return int(n or 0)'''
    if old_clear not in ct:
        raise SystemExit("clear OLD mismatch")
    ct = ct.replace(old_clear, new_clear)
    print("clear_temp updated")
else:
    print("clear already")

if "prefer first line title=" not in ct:
    old_prom = '''    db.put_fact("0x-WEB", f"chunk/{chunk_id}", summary[:4000])'''
    new_prom = '''    title = f"chunk/{chunk_id}"
    raw = row["text"] or ""
    if raw.startswith("title="):
        title = raw.split("\\n", 1)[0][6:].strip()[:160] or title
    db.put_fact("0x-WEB", title, summary[:4000])'''
    if old_prom not in ct:
        raise SystemExit("promote OLD mismatch")
    ct = ct.replace(old_prom, new_prom)
    print("promote fixed")
else:
    print("promote already")
cp.write_text(ct, encoding="utf-8")

# --- chamber prune ---
chp = Path("nova/chamber.py")
cht = chp.read_text(encoding="utf-8")
cht = cht.replace(
    'SEATS = ("claw", "qwen", "code")',
    'SEATS = ("claw", "code")  # pruned: qwen opt-in via seats=',
)
if "Lean MoE" not in cht:
    # replace from def round_robin through council
    start = cht.find("def round_robin")
    if start < 0:
        raise SystemExit("no round_robin")
    # keep ask_* above; replace round_robin + council at end
    head = cht[:start]
    tail = '''def round_robin(topic: str, problem: str, seats: tuple[str, ...] | None = None) -> dict:
    """Lean MoE: default claw+code. Pass seats=("claw","qwen","code") to include qwen."""
    case = case_id(topic)
    prompt = (
        f"CASE {case}\\nPROBLEM:\\n{problem}\\n"
        "Reply as design opinion: agree/disagree, top risk, next cut. Max 12 lines. No clarifying questions."
    )
    fn_map = {"claw": ask_claw, "qwen": ask_qwen, "code": ask_code}
    use = tuple(seats) if seats else SEATS
    out = {"case": case, "zulu": db.zulu(), "seats": {}, "seat_list": list(use)}
    for seat in use:
        fn = fn_map.get(seat)
        if not fn:
            continue
        try:
            opinion = fn(prompt)
            stored = store_temp(case, seat, opinion, cite=f"chamber.round:{seat}")
            out["seats"][seat] = {"ok": True, **stored, "opinion_head": opinion[:240]}
        except Exception as exc:
            breaklog.record("chamber", f"{seat}:{exc}", severity="warn", whi="Tx-TEMP")
            stored = store_temp(case, seat, f"ERROR: {exc}", cite="chamber.error")
            out["seats"][seat] = {"ok": False, **stored, "error": str(exc)}
    return out


def council(topic: str, steward_report: str, seats: tuple[str, ...] | None = None) -> dict:
    """Steward briefing -> lean round_robin. Default claw+code (pruned spine)."""
    return round_robin(topic, steward_report, seats=seats)
'''
    chp.write_text(head + tail, encoding="utf-8")
    print("chamber pruned")
else:
    chp.write_text(cht, encoding="utf-8")
    print("chamber seats line updated / already lean")

print("ALL_PATCH_OK")
