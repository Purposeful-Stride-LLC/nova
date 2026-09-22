import json
from pathlib import Path
import paramiko
from nova import db

HOST, USER, PW = "192.168.0.76", "mike", "mike"
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PW, timeout=20, allow_agent=False, look_for_keys=False)

def run(cmd, t=360):
    _, o, e = client.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

script = r"""
import time, subprocess, json
from pathlib import Path
subprocess.run(["ollama", "stop", "qwen:0.5b"], capture_output=True)
time.sleep(1)
t0 = time.perf_counter()
p = subprocess.run(
    ["ollama", "run", "qwen:0.5b", "Reply with exactly: COLD_NODE_OK"],
    capture_output=True, text=True, timeout=300,
)
ms = int((time.perf_counter() - t0) * 1000)
info = {"ok": p.returncode == 0, "ms": ms, "stdout": (p.stdout or "")[:300], "rc": p.returncode}
Path("/tmp/cold_ollama.json").write_text(json.dumps(info))
print(json.dumps(info))
"""
sftp = client.open_sftp()
with sftp.file("/tmp/cold_run.py", "w") as f:
    f.write(script)
out, err = run("python3 /tmp/cold_run.py")
print("COLD", out.strip(), err[:200])
out2, err2 = run(
    "ls -la /home/mike/Documents/data_science_at_the_command_line.pdf; "
    "file /home/mike/Documents/data_science_at_the_command_line.pdf; "
    "pdftotext -f 1 -l 2 /home/mike/Documents/data_science_at_the_command_line.pdf - 2>&1 | head -25"
)
print("BOOK", out2[:1200])
sftp.close()
client.close()

p = Path("STAGING/OG_DRILLS_ROUND2.json")
r = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"drills": {}}
try:
    cold = json.loads(out.strip().splitlines()[-1])
except Exception:
    cold = {"raw": out[-500:]}
r.setdefault("drills", {})["cold_ollama"] = cold
r["drills"]["ds_cli_book"] = {"snip": out2[:1500]}
r["hearthbeat"] = {"name": "Hearthbeat", "ids": ["hearth:tuf-hub", "hearth:og-ubuntu"]}
p.write_text(json.dumps(r, indent=2), encoding="utf-8")
db.put_fact("Ax-NODE", "og-drills-r2", json.dumps(r["drills"], default=str)[:3500], kind="probe")
print("cold_ms", cold.get("ms"), "ok", cold.get("ok"))
