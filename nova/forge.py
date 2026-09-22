"""Tool forge — daemon-shaped specs. Cite the origin. No silent writes."""

from __future__ import annotations

# name: job string the scheduler already understands
# every_s: suggested period
# cite: where the hand came from
# risk: report rank if it writes

FORGE = [
    {
        "name": "holmes",
        "job": "holmes",
        "every_s": 300,
        "cite": "NOVA awareness probes (psutil/opencv/loopback)",
        "does": "Read-only snapshot. observations table.",
        "risk": 0,
    },
    {
        "name": "hw-check",
        "job": "hw-check",
        "every_s": 600,
        "cite": "office.hw_check checksum",
        "does": "Compare USB/cam/cpu map. Rank-2 report on change.",
        "risk": 2,
    },
    {
        "name": "ollama-catalog",
        "job": "ollama-catalog",
        "every_s": 600,
        "cite": "Ollama POST /api/tags 127.0.0.1:11434",
        "does": "Stamp Ax-OLLAMA + bind employees.",
        "risk": 0,
    },
    {
        "name": "whistle",
        "job": "whistle",
        "every_s": 900,
        "cite": "Kyutai pocket-tts serve POST /tts form",
        "does": "One employee line. Serve must be up.",
        "risk": 0,
    },
    {
        "name": "cam-0",
        "job": "cam:0",
        "every_s": 300,
        "cite": "OpenCV VideoCapture index 0",
        "does": "One still → data/artifacts/cam_0.jpg Tx-CAM",
        "risk": 1,
    },
    {
        "name": "maintain",
        "job": "maintain",
        "every_s": 86400,
        "cite": "office/conversations word ranks",
        "does": "Retitle convs. No web.",
        "risk": 0,
    },
    {
        "name": "web",
        "job": "web:URL",
        "every_s": 0,
        "cite": "urllib + matrix.analyze. Steward URL only.",
        "does": "Strip → score → 0x-WEB or Tx-REJECT.",
        "risk": 1,
    },
    {
        "name": "history",
        "job": "history",
        "every_s": 0,
        "cite": "Chrome/Edge History SQLite copy",
        "does": "Tx-HIST url list. Does not auto /web.",
        "risk": 1,
    },
    {
        "name": "pdf",
        "job": "pdf:PATH",
        "every_s": 0,
        "cite": "pypdf text layer",
        "does": "Tx-PDF. Scanned pages stay empty.",
        "risk": 1,
    },
    {
        "name": "codesum",
        "job": "codesum:PATH",
        "every_s": 0,
        "cite": "ollama chat + reviewer mask",
        "does": "Folder vs file. Tx-CODE until promoted.",
        "risk": 1,
    },

    {
        "name": "openclaw-status",
        "job": "openclaw-status",
        "every_s": 600,
        "cite": "leash.openclaw_status http://127.0.0.1:18789",
        "does": "Probe lobster gateway. Mail openclaw@local. Ax-CLAW/Tx-CLAW.",
        "risk": 0,
    },
    {
        "name": "qwen-status",
        "job": "qwen-status",
        "every_s": 600,
        "cite": "leash.qwen_status + Ollama tags",
        "does": "Probe komodo CLI/settings. Mail qwen@local. Prefer codellama for codesum.",
        "risk": 0,
    },
    {
        "name": "camsee-0",
        "job": "camsee:0",
        "every_s": 0,
        "cite": "senses.save_still + optional moondream",
        "does": "Vision analysis loop with VLM. Steward-triggered; not default tick heat.",
        "risk": 1,
    },
    {
        "name": "workforce",
        "job": "workforce",
        "every_s": 0,
        "cite": "office.ensure_workforce",
        "does": "Upsert openclaw@ qwen@ seer@ ear@ clerk@ into employees.",
        "risk": 0,
    },
]


def listing() -> str:
    lines = []
    for t in FORGE:
        lines.append(
            f"{t['name']:16} job={t['job']:22} every={t['every_s']}s  cite={t['cite']}"
        )
        lines.append(f"{'':16} {t['does']}")
    return "\n".join(lines)


def suggest() -> list[tuple[str, int]]:
    return [(t["job"], t["every_s"]) for t in FORGE if t["every_s"] > 0]
