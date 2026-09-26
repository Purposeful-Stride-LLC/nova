# Paper trading module PLAN (own DB + WHI)
Status: to-build. Separate from palace. Aurelius drafts; steward integrates.

## Why separate
NOVA.db is palace/ops. Paper markets are experimental — own blast radius.
Cross-link via WHI facts citing paper:ids (do not melt tables into palace).

## Layout
nova/paper/ — broker.py, ledger.py, marks.py, whi_bridge.py
data/paper.db — accounts, positions, fills, marks, runs
Palace: Ax-PAPER / Tx-PAPER facts
Job paper-mark — mark-to-market only; never live orders

## Risk
max notional; paper_only=True hard-coded; never wipe NOVA.db for paper resets
