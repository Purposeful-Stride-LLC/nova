#===============================================================================
# NOVA TTS Daemon - Job Handler (Simplified)
#===============================================================================

"""
TTS Job Daemon — Conversational Speech Layer
Simple registration for TTS job handlers.
Usage: python nova/tts_daemon.py --register|--list
"""

import json, time, glob
from pathlib import Path
from datetime import datetime

sys = __import__('sys')
sys.path.insert(0, str(Path(__file__).parent))

JOB_DIR = Path.home() / ".openclaw" / "data" / "nova-daemon-tts"


def main():
    if len(sys.argv) < 2:
        print("Usage: python nova/tts_daemon.py [--register|--list]")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "--register":
        # Ensure job dir
        JOB_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create job file for chronicler voice
        job_data = {
            "name": "nova-tts-chronicler",
            "type": "tts_speech",
            "voice": "charles",
            "interval": 300,
            "status": "registered"
        }
        
        job_file = JOB_DIR / "chronicler_job.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f)
        
        print("TTS Job Registered: nova-tts-chronicler")
        print(f"  Location: {job_file}")
    
    elif cmd == "--list":
        # List jobs
        for f in sorted(JOB_DIR.glob("*_job.json")):
            with open(f) as fp:
                data = json.load(fp)
            print(f"\n{data['name']}")
            print(f"  Voice: {data.get('voice', 'unknown')}")
            print(f"  Status: {data.get('status', 'unknown')}")
    
    elif cmd == "--unregister":
        # Unregister by name (simplified)
        if len(sys.argv) < 3:
            print("Usage: python nova/tts_daemon.py --unregister <name>")
            return
        
        fname = f"{sys.argv[2]}_job.json"
        for f in JOB_DIR.glob("*_job.json"):
            if sys.argv[2] in f.name:
                f.unlink()
                print(f"Removed: {fname}")
                break
    
    elif cmd == "--loop":
        # Demo loop
        print("TTS Daemon Loop - Testing...")
        for i in range(3):
            time.sleep(5)
            dt = datetime.now().strftime("%H:%M:%S")
            print(f"[{dt}] Tick {i+1}: Polling TTS queue...")
    
    else:
        main()


if __name__ == "__main__":
    main()
