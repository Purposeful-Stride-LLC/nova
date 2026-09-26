from nova import db
con = db.connect()
for r in con.execute("select id,zulu,dest,kind,status,whi from packets where id>=7 order by id"):
    print(dict(r))
print("--- packet 8 reply tail ---")
print(con.execute("select body from packets where id=8").fetchone()["body"][-600:])
print("--- packet 11 ---")
print(con.execute("select body from packets where id=11").fetchone()["body"][:500])
