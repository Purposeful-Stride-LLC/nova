# OG Ubuntu — lid-closed beacon + tentacle always-on
Node: hearth:og-ubuntu · 192.168.0.76 · user mike · tentacle `~/pg/nova-tentacle`
Updated: 2026-09-22 06:02 CDT
**No passwords or tokens in this file or in unit Environment= lines.**

## 1) Disable suspend on lid close
```bash
# as mike (or with sudo where needed)
sudo mkdir -p /etc/systemd/logind.conf.d
sudo tee /etc/systemd/logind.conf.d/99-nova-lid.conf >/dev/null <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
IdleAction=ignore
EOF
sudo systemctl restart systemd-logind
# Verify: lid close should not suspend. Check:
gsettings get org.gnome.settings-daemon.plugins.power lid-close-ac-action 2>/dev/null || true
# Optional GNOME (if desktop session):
# gsettings set org.gnome.settings-daemon.plugins.power lid-close-ac-action 'nothing'
# gsettings set org.gnome.settings-daemon.plugins.power lid-close-battery-action 'nothing'
```

## 2) Prevent sleep / hybrid sleep (optional belt)
```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
# Undo later: sudo systemctl unmask …
```

## 3) systemd user linger (tentacle survives logout)
```bash
sudo loginctl enable-linger mike
loginctl show-user mike | grep Linger
```

## 4) Tentacle systemd user service
Create `~/.config/systemd/user/nova-tentacle.service`:
```ini
[Unit]
Description=NOVA tentacle job worker (Hearthbeat)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/pg/nova-tentacle
ExecStart=/usr/bin/python3 %h/pg/nova-tentacle/tentacle.py
Restart=always
RestartSec=5
# Do NOT put secrets here. Use a root-owned env file if ever needed.
Environment=PYTHONUNBUFFERED=1
Environment=NOVA_BEACON_PORT=41776
Environment=NOVA_JOBS_PORT=41777

[Install]
WantedBy=default.target
```
```bash
mkdir -p ~/pg/nova-tentacle/queue/{waiting,running,done,failed}
systemctl --user daemon-reload
systemctl --user enable --now nova-tentacle.service
systemctl --user status nova-tentacle.service --no-pager
```

## 5) Firewall UDP 41776 / 41777 (LAN only)
```bash
# ufw example — adjust interface/source to LAN
sudo ufw allow from 192.168.0.0/24 to any port 41776 proto udp comment 'NOVA beacon'
sudo ufw allow from 192.168.0.0/24 to any port 41777 proto udp comment 'NOVA jobs'
sudo ufw status | grep 4177 || true
ss -ulnp | grep -E '41776|41777' || true
```

## 6) Keepalive / beacon sanity
- Hub (TUF) should see periodic beacon from OG on 41776.
- Smoke: enqueue `queue.ping` envelope to OG waiting queue or UDP 41777; expect result JSON with matching id.
- If SSH from TUF is blocked, do these steps **on the OG keyboard/console**; do not embed credentials in docs.

## 7) PROOF to return to steward
Write `STAGING/OG_LID_CLOSED_PROOF.json` with: linger=yes/no, unit active=yes/no, ports listening, ping ok, lid policy note. No secrets.
