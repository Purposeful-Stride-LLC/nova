# NOVA Flow Diagrams

## 1) Grand Pipe: Main Architecture

```mermaid
graph TD
    A[Steward HIL] -->|control plane| B[TUI/GUI]
    B -->|palace DB access| C[(palace SQLite)]
    D[daemon tick] --> E[homes/ingest/mail]
    F[/ask command] --> G[Ollama inference]
    H[/claw command] --> I[127.0.0.1:18789]
    J[/qwen command] --> K[qwen --prompt]
    L[Ollama TTS service] -->|:8000| M[Audio output]
    I -.may visit.-> N[Grok API]
    K -.may visit.-> N[Grok API]
```

## 2) Sub-loop: Packet Processing

```mermaid
flowchart LR
    Start([packet received]) --> Tool{select tool}
    Tool --"one tool"--> Result[tool execution result]
    Result --> Check{ok?}
    Check --yes--> Tx[transmit] --> Wing[/wing process/]
    Wing --> More{more packets?}
    Check --no--> Report[report failure] --> More
    More --yes--> HIL[Steward HIL next packet]
    More --no--> Done([done])
```

## Architectural Principles

- Three processes stay three: steward, brain, leash.
- Claw is servant not merger; acts as executor, not data combiner.
- HIL (Horse Interface Layer) precedes all writes and external operations.
- Grok Automation is not an OpenClaw strap; optional external hook.
- Snap is not a real HWND; window handle abstraction only.
