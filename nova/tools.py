"""Named hands the daemon and TUI share. Schedule with /job add SECS name."""

TOOLS = {
    "holmes": "Read-only probe sweep. Safe. Suggested every 300s.",
    "maintain": "Retitle conversations from word ranks. Suggested daily.",
    "ollama-catalog": "GET /api/tags and stamp Ax-OLLAMA rows.",
    "web": "Not auto. Use /web URL. Quality-gated inject.",
    "pdf": "/pdf PATH  text extract → Tx then wing.",
    "codesum": "/codesum PATH  file or folder. Windows-safe colors.",
    "spyder": "/spyder  ping local /24 read-only.",
    "cam": "/cam [n|url]  one still.",
    "hunt": "/hunt Q  palace first.",
    "tts": "/tts TEXT  serve-first pocket.",
    "hw-check": "Checksum USB/cam/cpu map. Rank-2 report on change.",
    "cam:0": "/job add 15 cam:0   scheduled still.",
    "whistle": "Water cooler. 900s. Employee voice.",
}


def listing() -> str:
    return "\n".join(f"  {k:16} {v}" for k, v in TOOLS.items())


def suggested_jobs() -> list[tuple[str, int, str]]:
    return [
        ("holmes", 300, "awareness heartbeat"),
        ("ollama-catalog", 600, "keep model roster fresh"),
        ("maintain", 86400, "conversation titles"),
        ("hw-check", 600, "hardware checksum"),
        ("whistle", 900, "four times an hour max"),
        ("cam:0", 30, "still from camera 0 after /approve"),
    ]
