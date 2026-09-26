# PAPER_API_SKETCH.md
nova/paper/broker.py — fetch_bars(symbol, start, end) via yfinance or CSV; never place live orders
nova/paper/ledger.py — open_account, fill(side, qty, px), positions
nova/paper/marks.py — mark_all(account_id) -> writes marks + Tx-PAPER
nova/paper/whi_bridge.py — stamp(whi, title, body, cite)
Job paper-mark — sched daily; calls marks.mark_all
Hard flag PAPER_ONLY = True
