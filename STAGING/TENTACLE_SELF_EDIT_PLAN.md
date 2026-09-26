# Self-editing tentacle (NOVA edits the node)

Goal: Nova can harden/extend `~/pg/nova-tentacle` on a live node without always needing Michael at the keyboard.

## Trust ladder
1. **Observe** — Hearthbeat pong + metrics (always)
2. **Job** — allowlisted kinds via UDP 41777 / mail-slot
3. **Patch** — `kind=self_patch` applies a signed diff to allowlisted paths only
4. **Restart** — `kind=self_restart` (HIL or hub policy)
5. **SSH** — human/steward escape hatch when beacon down

## Allowlisted editable paths
- `bin/tentacle_node.py` (versioned backups `bin/.bak/`)
- `bin/plugins/*.py` (new abilities)
- `MESH.json`, `NODE_ID`
- **Never** auto-edit: `~/.ssh`, secrets, arbitrary `/home`

## Self-patch job shape
```json
{
  "job_id": "...",
  "kind": "self_patch",
  "path": "bin/plugins/ffmpeg_still.py",
  "mode": "write",
  "bytes": "<text>",
  "sha256": "...",
  "hil": false
}
```
Node verifies sha256, writes under root, logs metric, optional soft-reload.

## Komodo playground
Linux node is Komodo’s home for code: DS-at-CLI pipelines, FreeCAD scripts, ffmpeg one-liners. Hub posts `dest=node:hearth:og-ubuntu` tasks; results return with timestamps for thrash accounting.
