# STT council
session: 20260921T0654-50c71291

## S1: Pick STT stack for TUF self-hosted
### claw
AGREE. Pilot `faster-whisper small/base.en` on CPU first (or tiny GPU) for STT; pair with Pocket TTS :8000 output via `winsound` normalization. Risk: Large models (>1GB RAM) may stall 8GB VRAM TUF if batched without yieldMs; OS-native Windows.Media.SpeechRecognition introduces cloud quirks breaking local sovereignty. Next cut: a) Spin `nova/ear_stt.py` with `sounddevice` mic hook; b) Write `Tx-EAR` facts + wav to `nova-out/artifacts`; c) Run HIL smoke test (10s speech → transcript); d) Log latency to `nova/metrics/stt.json`.

### code

Recommendation: Agree.

I recommend the pilot of faster-whisper small/base.en on CPU first (or tiny GPU) for speech-to-text for blind/STT users and hands-free steward. This STT stack is fast, Python-friendly, and has good default accuracy. Additionally, it is suitable for the 8GB VRAM class of the TUF. The recommendation is to use the NOVA wrapper `nova/ear_stt.py` to write Tx-EAR facts and wav artifacts, mirroring the cam:0 pattern. The council should confirm/amend before installing.

### brief
Agree. Risk: Accuracy may drop with smaller models. Next cut: Test pilot with HIL cue word.

## S2: Mic path: push-to-talk HIL vs always-on
### claw
AGREE. Prefer push-to-talk or cue-word STT trigger: aligns with “gated action” sovereignty principle, avoids blind eavesdrop, and respects HIL oversight on 8GB VRAM TUF. Risk: Always-on mic risks silent transcript bloat in `Tx-EAR` if cue word logic fails or latency spikes block manual override. Next cut: a) Implement `nova/ear_stt.py` with `sounddevice` input gated by PTT/cue; b) Write fact + wav to `nova-out/artifacts`; c) Run HIL smoke test (PTT → transcript → log); d) Enforce non-goal audit (no cloud STT calls).

### code

I agree with the recommendation of using `faster-whisper` small/base.en on CPU for initial testing, and the use of sounddevice/pyaudio for mic input. The choice of cue word is up to the user, but it is recommended to use a push-to-talk approach to ensure privacy and security.

Regarding the non-goals, it is important to note that the use of a cloud STT service is not in the scope of this assessment, and the recommendation is to focus on using a local Ollama + Python on TUF for the STT functionality. Additionally, the use of a different TTS service, such as Pocket TTS, is not within the scope of this assessment, and the recommendation is to continue using the Pocket TTS service.

Overall, the recommendation is to use `faster-whisper` small/base.en on CPU for initial testing, and to use sounddevice/pyaudio for mic input. The use of a push-to-talk approach is also recommended to ensure privacy and security.

### brief
Agree. Risk: faster-whisper accuracy may degrade on CPU without GPU. Next cut: validate Tx-EAR artifact alignment with cam:0 pattern.

## S3: Wire shape: nova/ear_stt like cam:0
### claw
AGREE. Wire `nova/ear_stt.py` exactly like `cam:0(900)` job: 1) Gated PTT/cue word input via `sounddevice`; 2) Write `Tx-EAR` facts + `.wav` artifact to `nova-out/artifacts/`; 3) Mirror `cam:0` metadata pattern (`source=mic`, `fixed|dynamic`, `tz=zulu`); 4) Emit HIL log on each transcript. Risk: Blind mirroring assumes identical resource budgets—mic burst noise may clog SQLite if no vacuum-check in `maintain`. Next cut: a) Draft `ear_stt.py` with yieldMs=900s between wakes; b) Implement metadata schema in `NOVA.db`; c) Run HIL smoke test (10s speech → Tx-EAR row).

### code

Yes, I agree that Tx-EAR and wav artifact are good options for speech-to-text for blind/STT users and hands-free steward.

I recommend that the steward pilot faster-whisper small/base.en on CPU first or a tiny GPU, mic via sounddevice/pyaudio, and NOVA wrapper `nova/ear_stt.py` writing Tx-EAR facts + wav artifact - mirroring the cam:0 pattern.

Council should confirm/amend before installing.

I also agree that cloud STT, replacing Pocket TTS, and always-on eavesdrop without HIL cue word are non-goals.

### brief
Agree. Risk: Small model may miss nuanced speech. Next cut: Pilot Tx-EAR + wav artifact with wrapper.
