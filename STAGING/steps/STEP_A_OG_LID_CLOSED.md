# STEP A — Apply OG lid-closed beacon (Cassius/metal)
GOAL: Follow STAGING/OG_LID_CLOSED_BEACON.md on node hearth:og-ubuntu.
DO: disable suspend on lid, systemd tentacle unit, linger, firewall UDP 41776/41777, keepalive. No passwords in files.
DONE when: beacon visible from hub; tentacle accepts queue.ping.
PROOF: systemctl is-active output + ss -ulnp ports + one ping result JSON
OUT: STAGING/OG_LID_CLOSED_PROOF.json
