# PAPER_SCHEMA.md (steward draft after Aurelius timeout)
SQLite: data/paper.db (NOT NOVA.db)

## accounts
id INTEGER PK, name TEXT, currency TEXT DEFAULT USD, max_notional REAL, paper_only INTEGER DEFAULT 1, zulu TEXT

## runs
id INTEGER PK, account_id INT, strategy TEXT, status TEXT, started TEXT, ended TEXT, notes TEXT

## positions
id INTEGER PK, account_id INT, symbol TEXT, qty REAL, avg_cost REAL, opened TEXT, closed TEXT NULL

## fills
id INTEGER PK, account_id INT, run_id INT NULL, symbol TEXT, side TEXT, qty REAL, price REAL, zulu TEXT, cite TEXT

## marks
id INTEGER PK, account_id INT, symbol TEXT, px REAL, zulu TEXT

## WHI bridge (palace facts, not rows in paper.db)
Ax-PAPER — account/run summary cite paper:account:<id>
Tx-PAPER — fill/mark/error cite paper:fill:<id>
