# STEP P1 — leash.proof_tree
GOAL: Add proof_tree(paths) to nova/leash.py returning tree+sha256+bytes_total. No GPU.
DO: Write helper only under nova-out first OR patch leash.py overlay ≤40 lines. Hash file bytes sha256. Skip missing paths with Tx note.
DONE when: import smoke + one file hash matches.
PROOF: bytes=N tree=count sha256=…
OUT: nova-out/leash_proof_tree.py or patched nova/leash.py
