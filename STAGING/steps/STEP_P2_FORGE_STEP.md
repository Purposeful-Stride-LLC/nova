# STEP P2 — forge_step(step_path)
GOAL: Read a STAGING/steps/*.md STEP, execute write/copy rules, return mail job result envelope with proof.
DO: Prefer nova-out implementation first. No secrets. No DB wipe.
DONE when: running on STEP_P1 produces valid result JSON.
PROOF: bytes + tree + sha256 of artifacts
OUT: nova-out/forge_step.py
