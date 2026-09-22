# STEP — Profile OG Ubuntu LAN node (for Cassius / metal)

GOAL: Inventory Michael's older Ubuntu laptop as a NOVA-acquired CPU compute node.

DO:
1. From TUF (or the Ubuntu box itself), record: hostname, IP on LAN, Ubuntu version, CPU cores/RAM, which ollama, ollama list tags.
2. Confirm SSH from TUF works (user + key). Do NOT print private key material.
3. Write STAGING/OG_UBUNTU_NODE_PROFILE.json with fields matching NEED_OG_UBUNTU_NODE.md inventory.
4. Note older model tags vs TUF — list differences briefly in STAGING/OG_UBUNTU_MODEL_DELTA.md.

DONE when:
- Profile JSON exists and SSH smoke is true/false with error if false.
PROOF: bytes=N of the profile JSON on DONE line.

OUT: STAGING/OG_UBUNTU_NODE_PROFILE.json + STAGING/OG_UBUNTU_MODEL_DELTA.md