# data/queue — waiting work (filesystem)
Updated: 2026-09-22 06:02 CDT

Subdirs (create on metal if missing):
- `waiting/` — envelopes not yet claimed
- `running/` — claimed by worker (atomic rename from waiting)
- `done/` — success + PROOF
- `failed/` — timeout/error

See `STAGING/HEARTHBEAT_MAIL_JOB_SCHEMA.md` for JSON envelope + result format.
Palace `packets` table remains mail law; this tree is the durable waiting queue Michael named as missing.
