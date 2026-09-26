import json
from nova import db, chamber

case = "20260919T1334-f4b6ead4"
con = db.connect()
for title in [f"chamber/{case}/claw", f"chamber/{case}/qwen", f"chamber/{case}/code"]:
    row = con.execute("SELECT body FROM facts WHERE whi='Tx-TEMP' AND title=?", (title,)).fetchone()
    print("====", title, "====")
    if row:
        b = json.loads(row["body"])
        print(b.get("opinion","")[:1200])
    print()
