"""List all database tables and their schema."""
from nova import db

con = db.connect()
print("=== DATABASE TABLES ===")
for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    table_name = row[0]
    print(f"\n--- {table_name} ---")
    schema = con.execute(f"PRAGMA table_info({table_name})").fetchall()
    for col in schema:
        print(f"  {col[1]} ({col[2]})")
con.close()
