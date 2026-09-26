# OG lid-closed beacon — applied 2026-09-22T11:03:10Z

- SSH key auth: TUF `%USERPROFILE%\.ssh\id_ed25519_nova_og` → mike@192.168.0.76 authorized_keys
- systemd user service `nova-tentacle.service` enabled+active (UDP 41776 beacon, 41777 jobs)
- `loginctl linger=yes` for mike
- logind: HandleLidSwitch=ignore (and external/docked); IdleAction=ignore
- GNOME lid-close ac/battery = nothing; sleep-inactive = nothing
- Password was used once for key+sudo harden; NOT stored in palace/git. Rotate the Linux login password.

Smoke: `ssh -i ~/.ssh/id_ed25519_nova_og mike@192.168.0.76 'systemctl --user is-active nova-tentacle'`
