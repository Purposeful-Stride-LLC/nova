from nova import db
from collections import Counter
con = db.connect()
facts = con.execute("select whi, count(*) c from facts group by whi order by c desc").fetchall()
pkts = con.execute("select whi, count(*) c from packets group by whi order by c desc").fetchall()
print("FACTS WHI:")
for r in facts: print(" ", dict(r))
print("PACKETS WHI:")
for r in pkts: print(" ", dict(r))
# prefix health
bad = []
for table in ("facts","packets"):
    for r in con.execute(f"select id, whi from {table}"):
        w = (r["whi"] or "")
        if not (w.startswith("Ax-") or w.startswith("Tx-") or w.startswith("0x-")):
            bad.append((table, r["id"], w))
print("BAD_WHI", bad[:20], "count", len(bad))
print("SAMPLE facts titles", [dict(r) for r in con.execute("select id,zulu,whi,title from facts order by id desc limit 8")])
