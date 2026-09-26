# NOVA daemon council
session: 20260921T0538-50c71291

## D1: Definition of purpose of the NOVA daemon
### claw
AGREE. Purpose: NOVA daemon is a lean sovereign awareness loop that maintains palace WHI state via gated HIL jobs—never autonomous action or cloud sync. Non-goals: 1) Cloud dependencies (Ollama/SQLite local-only), 2) Forced execution without yieldMs, 3) Centralized authority override. Risk: Overloading daemon jobs on 8GB VRAM TUF risks thermal throttling if HIL gates absent. Next cut: a) Audit `holmes/maintain/whistle/cam` intervals for conflicts; b) Wire `yieldMs=5000` between job wakes; c) Log daemon state to `nova-out/daemon_status.json`.

### code

* The purpose of the NOVA daemon is to manage the various processes and jobs on the NOVA system, ensuring that they are running smoothly and efficiently.
* Non-goals include the ability to perform complex tasks, handle large amounts of data, or provide advanced analytics capabilities.
* One risk of the current NOVA daemon structure is that it may become difficult to manage and maintain over time, leading to potential system failures or inefficiencies.
* One next cut for the NOVA daemon would be to implement a more modular and scalable architecture, allowing for easier addition of new processes and jobs in the future.

### brief
Agree  
Risk: Resource contention in holmes/maintain tasks  
Next cut: TTS optimization for pocket mode  
Purpose: Ensure seamless TTS playback via anna/:8000  
Non-goals: No real-time audio processing, No external dependencies, No manual intervention

promoted: {'ok': True, 'case': '20260921T0538-d6a98295', 'promoted': 3, 'whi': 'Ax-CHAMBER'}

## D2: Current form vs ideal form for that purpose
### claw
AGREE. Current gaps: scheduler lacks `cron` clarity (hardcoded timers vs declarative intervals); no HIL gates before actions (blind wake/rerun); ingest_pipe drain manual instead of auto-drain in `maintain`; council promote optional not policy; awareness L0 absent to alert on palace lag. Ideal: explicit `nova/daemon/cron.txt` with interval+gate flags; auto-drain pipe; `whistle` emits L0 if WHI lags >5min. Risk: Idealizing assumes stable TUF power—loss triggers silent failover, breaking sovereignty traceability without HIL override. Next cut: a) Draft `cron.txt` with yieldMs gates; b) Wire ingest_pipe auto-drain; c) Implement L0 monitor in `whistle`.

### code
timed out

### brief
Amend. Risk: Resource underutilization in holmes 300s. Next cut: Prioritize TTS resource reallocation.

promoted: {'ok': True, 'case': '20260921T0542-1b6804ec', 'promoted': 3, 'whi': 'Ax-CHAMBER'}

## D3: Peer daemons / similar systems
### claw
AGREE. Analogues: systemd timers (steal interval semantics), cron+scripts (refuse rigid scheduling), Home Assistant (steal entity registry for sense mapping), Borg agents (refuse centralized control plane). Risk: Blindly stealing features could introduce non-sovereign dependencies (e.g., HA cloud sync) or break SQLite palace isolation on TUF. Next cut: a) Extract `systemd` timer intervals into `nova/daemon/cron.txt`; b) Audit `Home Assistant` entity registry for local-first cam metadata schema; c) Reject Borg-style central authority patterns in `leash.py`.

### code
Agree, but with two amendments:

1. Use a different playback method to prevent any potential issues with the winsound library.
2. Implement additional checks to ensure the audio files are being played back correctly and without any errors.

### brief
Agree. Risk: Data integrity via stolen analogs. Next cut: Test analogs in sandboxed environments.

promoted: {'ok': True, 'case': '20260921T0546-1fdd86c4', 'promoted': 3, 'whi': 'Ax-CHAMBER'}

## D4: Best performance vs actual accomplishments
### claw
AGREE. Ideal metrics (tick latency <5s, job success >95%, palace growth stable, TTS play_ok=100%, RAG hit rate >80%) vs actual: holmes/whistle often timeout on 8GB VRAM; cam:0 lag spikes; TTS silent bursts; RAG misses due to lack of WHI classify. Risk: Blindly chasing metrics without HIL gates risks thermal throttling or data corruption from forced retries. Next cut: a) Define `nova/metrics/baseline.json` with realistic targets; b) Instrument daemon jobs with `yieldMs` and latency logging; c) Run HIL healthcheck every 6h via `whistle`.

### code
Agree/Amend.

Risk: Lack of consistency in job scheduling and playback.

Next cut: Consider integrating more advanced AI tools for job scheduling and playback.

### brief
Amend. Risk: Underutilized TTS resources (anna/:8000). Next cut: Optimize TTS allocation for holmes 300s.

promoted: {'ok': True, 'case': '20260921T0548-7144799b', 'promoted': 3, 'whi': 'Ax-CHAMBER'}

## D5: Integration and functionality improvements
### claw
AGREE. Top 5 ordered cuts:  
1) **Ingest_pipe drain** into `maintain` cycle (auto-cleanup stale Ax/Tx).  
2) **Promote policy** for chamber temps → RAG after verdict (MOTION A default).  
3) **Pocket TTS play** hook in term.handle via winsound normalization (fixes silent chunks).  
4) **WHI awareness L0** monitor in `whistle` to alert if palace WHI lags >5min.  
5) **Aurelius STEP formats** enforce PROOF token before acceptance (audit trail integrity).  

Risk: Batched cuts without yieldMs risk thermal throttling on TUF 8GB VRAM chassis. Next cut: a) Sequence cuts with `yieldMs=3000` between steps; b) Validate each against `nova/metrics/baseline.json`; c) Log to `nova-out/audit.log`.

### code

Agree, with one risk and one next cut.

Risk: The integration of new features may lead to unexpected behavior or issues, which could impact the stability and performance of the system.

Next cut: The implementation of new features should be carefully planned and executed to ensure that they are integrated in a way that minimizes the risk of impacting the system's stability and performance. Additionally, ongoing monitoring and testing should be conducted to ensure that the new features are functioning as expected and do not cause any issues.

### brief
Agree. Risk: destabilizing existing workflows. Next cut: promote policy. Top 5 cuts: ingest_pipe drain, promote policy, Pocket TTS play, WHI awareness, Aurelius STEP formats.

promoted: {'ok': True, 'case': '20260921T0550-0d3fa46d', 'promoted': 3, 'whi': 'Ax-CHAMBER'}
