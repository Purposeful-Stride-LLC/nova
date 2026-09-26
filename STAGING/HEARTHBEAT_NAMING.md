# Hearthbeat — beacon naming + multi-node convention

Steward | 2026-09-21 ~05:11 CT | Michael: beacon needs a name; more computers coming

## Service name
**Hearthbeat** — the homestead mesh beacon (heartbeat for the hearth).

- Protocol family: Hearthbeat / NMB v1
- Ports (locked): UDP **41776** presence, UDP **41777** jobs
- Online signal: missed 3 pongs → node stale; SSH is bootstrap/repair, not liveness

## Node ID convention
```
hearth:<role>-<shortname>
```

| ID | Meaning |
|---|---|
| `hearth:tuf-hub` | GPU hub / palace source of truth (this TUF) |
| `hearth:og-ubuntu` | LinuxBox1 CPU tentacle (first slave) |
| `hearth:spare-laptop` | next computer when back |
| `hearth:console-<tag>` | future console bridge |
| `nova:<name>` | grade=full peer palace (promoted tentacle) |

Rules:
- lowercase, hyphenated shortname
- `hearth:` prefix = mesh participant
- `role` optional in shortname: `hub`, `og`, `spare`, …
- Inventory key == node id; beacon `from` / `to` use the same string

## Packet addresses (mail)
```
node:hearth:og-ubuntu     # tentacle jobs
hub:hearth:tuf-hub        # replies / HIL
nova:<id>                 # full peer
```

## Multi-node growth
When the other computer returns: new inventory row + same Hearthbeat ports + unique id. Hub fans pings; each pong carries `grade`, `abilities`, `load`.
