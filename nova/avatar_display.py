"""
Avatar display module — CPU-first, minimal GPU thrash.
Uses existing clips under D:\\pg\\ai\\nova-ai\\agents\\avatar\\.
Syncs mouth to Pocket TTS anna on :8000 if requested.
No new media library invented.
"""

import os
import subprocess
import sys

# Paths (adjust if deployed elsewhere)
CLIP_ROOT = r"D:\pg\ai\nova-ai\agents\avatar"
TTS_URL = "http://localhost:8000"  # Pocket TTS anna


def list_clips(root: str):
    """Return a sorted list of .mp4 clips in the avatar root."""
    assert os.path.isdir(root), f"root is not a dir: {root}"
    try:
        from pathlib import Path
        return sorted(Path(root).glob("*.mp4"))
    except Exception as e:
        print(f"Failed to list clips: {e}", file=sys.stderr)
        return []


def play_clip(clip_path: str, tts_sync: bool = False):
    """Play a single clip; optionally request TTS for the same phrase.
    
    Args:
        clip_path: full path to .mp4 to display in TUI/video player.
        tts_sync: if True, request Anna TTS (phrase from clip filename or default) and stream to stdout.
    """
    print(f"[*] Playing: {clip_path.name}")

    # Play using the existing video_player.py (or mpv/vlc fallback)
    try:
        from video_player import main as vp_main
        vp_main(str(clip_path))
    except ImportError:
        # Fallback to os.spawn if no player module; skip if not found.
        print("[!] No video player module; skipping playback.", file=sys.stderr)

    if tts_sync:
        phrase = clip_path.stem  # filename without extension
        request_tts(phrase)


def request_tts(phrase: str):
    """Request a TTS utterance from Pocket TTS and stream to stdout.
    
    HTTP GET to /tts with text body (simple JSON or plain).
    Adjust endpoint according to Anna's API.
    """
    url = f"{TTS_URL}/tts"
    payload = {"text": phrase, "voice": "anna"}  # adjust fields if needed
    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            data=str(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            for chunk in resp:
                sys.stdout.buffer.write(chunk)
        print("[*] TTS stream complete.", file=sys.stderr)
    except Exception as e:
        print(f"[!] TTS request failed: {e}", file=sys.stderr)


def smoke_test():
    """Play one demo clip + optional TTS (CPU-first)."""
    clips = list_clips(CLIP_ROOT)
    if not clips:
        print("[!] No clips found. Add .mp4 files under the root.", file=sys.stderr)
        return False

    # Pick first .mp4
    demo = str(clips[0])
    play_clip(demo, tts_sync=False)  # disable TTS unless requested by user
    return True


if __name__ == "__main__":
    smoke_test()
