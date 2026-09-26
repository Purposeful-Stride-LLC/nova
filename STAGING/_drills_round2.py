import os
﻿import json, time, socket, subprocess
from pathlib import Path
import paramiko

HOST, USER = "192.168.0.76", "mike"
PW = os.environ.get("NOVA_SSH_PW", "")  # redacted for public publish
REMOTE = "/home/mike/pg/nova-tentacle"
STAGING = Path(r"Documents\NOVA\NOVA_fieldkit_v1_4\STAGING")
KIT = Path(r"Documents\NOVA\NOVA_fieldkit_v1_4")

def udp_job(job, wait=300.0, port=41777):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(wait)
    t0 = time.perf_counter()
    sock.sendto(json.dumps(job).encode(), (HOST, port))
    try:
        data, _ = sock.recvfrom(65535)
        rtt = (time.perf_counter() - t0) * 1000
        body = json.loads(data.decode("utf-8", "replace"))
        return {"rtt_ms": round(rtt, 1), "body": body}
    except Exception as e:
        return {"rtt_ms": round((time.perf_counter() - t0) * 1000, 1), "error": f"{type(e).__name__}: {e}"}
    finally:
        sock.close()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PW, timeout=20, allow_agent=False, look_for_keys=False)

def run(cmd, t=300):
    _, out, err = client.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", "replace"), err.read().decode("utf-8", "replace"), out.channel.recv_exit_status()

results = {"zulu": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "drills": {}}

# --- cold-start ollama: stop model runners if any, then time ---
print("COLD OLLAMA...")
out, err, rc = run("""
# stop serving models to force cold-ish load
pkill -f 'ollama runner' 2>/dev/null || true
sleep 2
# drop file mail job for timed gen + also record
python3 - <<'PY'
import time, subprocess, json
from pathlib import Path
model='qwen:0.5b'
prompt='Reply with exactly: COLD_NODE_OK'
t0=time.perf_counter()
p=subprocess.run(['ollama','run',model,prompt], capture_output=True, text=True, timeout=300)
ms=int((time.perf_counter()-t0)*1000)
Path('/home/mike/pg/nova-tentacle/outbox/cold-ollama.result.json').write_text(json.dumps({
  'ok': p.returncode==0, 'model': model, 'ms': ms, 'stdout': (p.stdout or '')[:500],
  'stderr_tail': (p.stderr or '')[-300:], 'rc': p.returncode
}, indent=2))
print(ms)
PY
""")
print("cold local", out.strip(), err[:200])
sftp = client.open_sftp()
try:
    with sftp.file(f"{REMOTE}/outbox/cold-ollama.result.json", "r") as f:
        results["drills"]["cold_ollama"] = json.loads(f.read().decode())
except Exception as e:
    results["drills"]["cold_ollama"] = {"error": str(e), "out": out[:500]}

# warm UDP compare
print("WARM UDP OLLAMA...")
results["drills"]["warm_ollama_udp"] = udp_job({
    "job_id": "warm-ollama-1", "kind": "ollama_gen", "model": "qwen:0.5b",
    "prompt": "Reply with exactly: WARM_NODE_OK", "timeout": 240
}, wait=260)

# --- ffmpeg still from cam ---
print("FFMPEG CAM...")
out, err, rc = run("""
mkdir -p /home/mike/pg/nova-tentacle/captures
# try video0 then video1; 1 frame jpeg
STILL=/home/mike/pg/nova-tentacle/captures/still_$(date -u +%Y%m%dT%H%M%SZ).jpg
for DEV in /dev/video0 /dev/video1; do
  if [ -e "$DEV" ]; then
    echo TRY $DEV
    # v4l2 still via ffmpeg; short timeout
    timeout 20 ffmpeg -y -f v4l2 -video_size 640x480 -i "$DEV" -frames:v 1 "$STILL" 2>/tmp/ff_cam.err && break
  fi
done
ls -la "$STILL" 2>/dev/null || ls -la /home/mike/pg/nova-tentacle/captures | tail -5
tail -20 /tmp/ff_cam.err 2>/dev/null
python3 - <<PY
import json, os
from pathlib import Path
cap=Path('/home/mike/pg/nova-tentacle/captures')
stills=sorted(cap.glob('still_*.jpg'))
info={'ok': bool(stills), 'n': len(stills)}
if stills:
  p=stills[-1]
  info.update({'path': str(p), 'bytes': p.stat().st_size})
Path('/home/mike/pg/nova-tentacle/outbox/ffmpeg-still.result.json').write_text(json.dumps(info, indent=2))
print(json.dumps(info))
PY
""")
print(out[-800:], err[:300])
try:
    with sftp.file(f"{REMOTE}/outbox/ffmpeg-still.result.json", "r") as f:
        results["drills"]["ffmpeg_still"] = json.loads(f.read().decode())
except Exception as e:
    results["drills"]["ffmpeg_still"] = {"error": str(e), "out": out[-1000:]}

# --- curl scout HIL-approved fetch of a benign public page ---
print("CURL SCOUT...")
out, err, rc = run("""
URL='https://example.com'
OUT=/home/mike/pg/nova-tentacle/captures/scout_example.html
T0=$(date +%s%3N)
curl -fsSL --max-time 20 -A 'NOVA-tentacle-scout/0.1 (HIL)' -o "$OUT" "$URL"
RC=$?
T1=$(date +%s%3N)
python3 - <<PY
import json, pathlib, os
p=pathlib.Path('/home/mike/pg/nova-tentacle/captures/scout_example.html')
info={
 'ok': p.exists() and p.stat().st_size>0,
 'url': 'https://example.com',
 'path': str(p) if p.exists() else None,
 'bytes': p.stat().st_size if p.exists() else 0,
 'hil': True,
 'note': 'benign example.com fetch for scout timing'
}
pathlib.Path('/home/mike/pg/nova-tentacle/outbox/curl-scout.result.json').write_text(json.dumps(info, indent=2))
print(json.dumps(info))
PY
""")
print(out.strip())
try:
    with sftp.file(f"{REMOTE}/outbox/curl-scout.result.json", "r") as f:
        results["drills"]["curl_scout"] = json.loads(f.read().decode())
except Exception as e:
    results["drills"]["curl_scout"] = {"error": str(e)}

# --- FreeCAD headless ---
print("FREECAD...")
out, err, rc = run("""
which freecad freecadcmd FreeCADCmd 2>/dev/null
# headless version / python one-liner
python3 - <<'PY'
import json, shutil, subprocess, time
from pathlib import Path
cmds = [shutil.which(x) for x in ('freecadcmd','FreeCADCmd','freecad')]
cmds = [c for c in cmds if c]
info={'ok': False, 'cmds': cmds}
out_dir=Path('/home/mike/pg/nova-tentacle/captures')
out_dir.mkdir(exist_ok=True)
script=out_dir/'fc_headless.py'
script.write_text('''
import FreeCAD as App
doc=App.newDocument('NovaProbe')
box=doc.addObject('Part::Box','Box')
box.Length=10; box.Width=5; box.Height=2
doc.recompute()
doc.saveAs('/home/mike/pg/nova-tentacle/captures/nova_probe_box.FCStd')
print('SAVED')
''')
t0=time.perf_counter()
if cmds:
    # FreeCADCmd -c or freecad -c
    exe=cmds[0]
    try:
        p=subprocess.run([exe, str(script)], capture_output=True, text=True, timeout=120)
        info.update({'ok': p.returncode==0 or 'SAVED' in (p.stdout or ''), 'ms': int((time.perf_counter()-t0)*1000),
                     'stdout': (p.stdout or '')[-500:], 'stderr': (p.stderr or '')[-500:], 'exe': exe})
    except Exception as e:
        # try freecad -c
        try:
            p=subprocess.run([exe, '-c', str(script)], capture_output=True, text=True, timeout=120)
            info.update({'ok': 'SAVED' in (p.stdout or '') or p.returncode==0, 'ms': int((time.perf_counter()-t0)*1000),
                         'stdout': (p.stdout or '')[-500:], 'stderr': (p.stderr or '')[-500:], 'exe': exe+ ' -c'})
        except Exception as e2:
            info['error']=str(e2)[:300]
else:
    # python freecad module?
    try:
        t0=time.perf_counter()
        import FreeCAD as App
        info['import_ok']=True
        info['ms']=int((time.perf_counter()-t0)*1000)
        info['ok']=True
    except Exception as e:
        info['error']=f'no freecadcmd: {e}'
fc=Path('/home/mike/pg/nova-tentacle/captures/nova_probe_box.FCStd')
if fc.exists():
    info['artifact_bytes']=fc.stat().st_size
    info['artifact']=str(fc)
    info['ok']=True
Path('/home/mike/pg/nova-tentacle/outbox/freecad-headless.result.json').write_text(json.dumps(info, indent=2))
print(json.dumps(info)[:800])
PY
""")
print(out[-1000:], err[:400])
try:
    with sftp.file(f"{REMOTE}/outbox/freecad-headless.result.json", "r") as f:
        results["drills"]["freecad_headless"] = json.loads(f.read().decode())
except Exception as e:
    results["drills"]["freecad_headless"] = {"error": str(e), "out": out[-800:]}

# book exists?
out, err, rc = run("ls -la /home/mike/Documents/data_science_at_the_command_line.pdf; pdftotext -f 1 -l 3 /home/mike/Documents/data_science_at_the_command_line.pdf - 2>/dev/null | head -40")
results["drills"]["ds_cli_book"] = {"ls_and_snip": out[:1500], "err": err[:200]}

sftp.close()
client.close()

STAGING.joinpath("OG_DRILLS_ROUND2.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print("WROTE", STAGING / "OG_DRILLS_ROUND2.json")
print(json.dumps({k: {kk: vv for kk,vv in (v.items() if isinstance(v, dict) else []) if kk in ('ok','ms','bytes','path','rtt_ms','model','stdout','error','artifact','artifact_bytes','body') or kk=='ok'} if isinstance(v, dict) else v for k,v in results['drills'].items()}, default=str)[:2000])
# slim print
for k,v in results['drills'].items():
    if isinstance(v, dict):
        slim={x:v.get(x) for x in ('ok','ms','bytes','path','rtt_ms','model','error','artifact_bytes','stdout') if x in v}
        if 'body' in v and isinstance(v['body'], dict):
            slim['job_ms']=v['body'].get('ms'); slim['ok']=v['body'].get('ok'); slim['stdout']=(v['body'].get('stdout') or '')[:80]
        print(k, slim)
