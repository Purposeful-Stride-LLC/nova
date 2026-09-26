# Plan after inventory (do not rediscover blindly)

## Already on OG (use these; do not repeat cold)
- Tentacle root `~/pg/nova-tentacle` with inbox/outbox/log
- Outbox PROOF already: boot-discover, hub-map-1/2, ffmpeg-still, freecad-headless, curl-scout
- Abilities: cpu_llm, shell, net, fs_map, cam, mic
- Ollama models listed (qwen:0.5b primary for CPU council)
- Cam devices /dev/video0,/dev/video1
- TUF acquisition pack: OG_PROFILE, OG_CODESUM_pg (281 files), doctrine

## Protocol change (2026-09-22)
Firewall/WUV now **TCP** for the mail channel.
- **41776/tcp** — beacon ping/pong
- **41777/tcp** — job submit/result (4-byte length + JSON)
- File inbox/outbox remains fallback
- Hub module: `nova/hearthbeat.py` on TUF

## Next work (ordered, uses existing)
1. Deploy TCP tentacle; smoke ping+health from TUF hearthbeat
2. Job `sys_inventory` once over TCP → compare to STAGING/acquisition (delta only)
3. Job `apt_inventory` / `which_tools` if not already in outbox
4. Stand up OG `council_worker` consuming queue topics; results via 41777 TCP
5. Education/WHI gap councils enqueue from TUF; OG runs CPU qwen:0.5b; thermal cooldown matrix from measured ms
6. LAN ARP list — label ours — acquire next device with same inventory-first rule
