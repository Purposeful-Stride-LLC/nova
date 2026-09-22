# Existing DB to WHI compatible
2026-09-21 02:17 local

## Reality (live check this cycle)
- facts.whi TEXT already populated; blank whi count = 0
- Indexes: idx_facts_whi, idx_facts_whi_title, idx_chunks_whi, idx_chunks_status_whi
- Earlier no-such-table was a false alarm - idx_facts_whi is an INDEX
- whi.ensure_indexes(con) now called from maintain
- Hexclass folded into nova/hexclass_table.json + whi.py
- live chunks ~98

## Compat posture
Already WHI-compatible at column+index layer. No rebuild needed.

## Optional later
- GUI/deck query by whi prefix
- classify+UPDATE only if blank whi appears

## Do not
- Rebuild palace from thumb
- Change WHI codes on historical valid rows
- Wipe temps without drain_through_pipe
