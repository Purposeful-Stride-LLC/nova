# How the pets and mail work (human readable)
Updated: 2026-09-22 06:02 CDT

NOVA is a small homestead agent on your PC. It keeps a private database (the palace) and talks to a few “pets” over local mail packets — not WhatsApp, not the public internet by default.

**Qwen / Komodo** is the coding pet. When you ask for a code change, NOVA can leash Qwen Code to draft a patch. Komodo is supposed to write drafts into STAGING or nova-out, not blow away your live database.

**Aurelius / OpenClaw (Claw)** is the execute pet. After a draft looks right, Claw forges it in: applies the step, then must prove what changed with a file tree and checksums (PROOF). Claw is a servant door on the machine (local port), not the owner of the palace.

**Mail / beacon (Hearthbeat)** is how work moves. The hub can shout a small UDP beacon so nodes know it is alive, and push jobs on another UDP port. Jobs are JSON envelopes with a verb, timeout, and a requirement for PROOF. There is a waiting queue on disk so work can sit until a node (including the older Ubuntu laptop with the lid closed) picks it up.

**Pocket TTS (anna)** can speak short lines on port 8000 when you want ears in the room. The GPU is shared — councils and pets should prefer a tiny model or CPU and not hog VRAM.

**You (steward)** stay in the loop. Nothing important promotes from STAGING into live `nova\` without you. The DEVLOG is the human diary of what we meant to do.
