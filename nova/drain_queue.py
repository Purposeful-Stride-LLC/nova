"""Drain board HTTP queue and report hit/miss counts."""
from nova import db
from nova.hands import web

def drain_and_report():
    con = db.connect()
    
    # Get all pending URLs
    rows = con.execute(
        "SELECT * FROM queue WHERE description LIKE 'http%' ORDER BY id DESC"
    ).fetchall()
    con.close()
    
    if not rows:
        print("✓ Queue is empty. Nothing to drain.")
        return
    
    hits = 0
    misses = 0
    
    print(f"\nDraining {len(rows)} pending HTTP URLs...\n")
    
    for row in rows:
        rec = dict(row)
        url = rec["description"]
        
        try:
            res = web.fetch(url)
            if res.get("ok"):
                status = "HIT"
                hits += 1
            else:
                status = "MISS"
                misses += 1
        except Exception as e:
            status = f"FAIL ({e})"
            misses += 1
        
        print(f"[{status}] {url[:80]}...")
    
    con = db.connect()
    # Mark all as done/fail
    for row in rows:
        rec = dict(row)
        con.execute(
            "UPDATE queue SET status='done' WHERE id=?",
            (rec["id"],)
        )
    con.commit()
    con.close()
    
    print(f"\n{'='*60}")
    print("BOARD QUEUE DRAIN REPORT")
    print(f"{'='*60}")
    print(f"Total URLs processed: {hits + misses}")
    print(f"HITS (successful ingest):   {hits}")
    print(f"MISS/Fails (rejected):      {misses}")
    print(f"{'='*60}")

if __name__ == "__main__":
    drain_and_report()
