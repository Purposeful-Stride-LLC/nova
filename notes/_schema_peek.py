from nova import db
con = db.connect()
print("TABLES:", [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1").fetchall()])
for t in ["facts","packets","employees","jobs","conversations"]:
    try:
        cols = con.execute(f"PRAGMA table_info({t})").fetchall()
        print(t, [c[1] for c in cols])
    except Exception as e:
        print(t, e)
