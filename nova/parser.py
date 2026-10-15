"""Peel structured returns BEFORE the booth paints. No LLM."""

from __future__ import annotations

import re

from nova import pocket

# Models invent wrappers. Catch the common ones.
SPEAK_BLOCK = re.compile(
    r"\[(?:speak|voice|say|tts|notice)\s*[:\s]+([a-z0-9_@]+)\](.*?)\[/\s*(?:speak|voice|say|tts|notice)\s*\]",
    re.I | re.S,
)
SPEAK_LINE = re.compile(
    r"^(?:SPEAK|VOICE|SAY|TTS|NOTICE)\s*[:\|]\s*([a-z0-9_@]+)\s*[:\|]\s*(.+)$",
    re.I | re.M,
)

SPEAK_COLON = re.compile(
    r"^(?:SPEAK|VOICE|SAY|TTS)\s+([a-z0-9_@]+)\s*:\s*(.+)$",
    re.I | re.M,
)
SPEAK_XML = re.compile(
    r"<(?:speak|voice)\s+(?:voice|name)=[\"']([a-z0-9_]+)[\"']\s*>(.*?)</(?:speak|voice)>",
    re.I | re.S,
)

SPEAK_MD = re.compile(
    r"\*\*(?:speak|say)\s+([a-z0-9_]+)\*\*\s*[:\-]?\s*(.+)",
    re.I,
)

GRAMMAR = """
SPEECH RULES (required, exact — any LLM must follow):
To speak aloud, emit EXACTLY one tagged line after your visible answer:

[speak anna] One short sentence under twelve words. [/speak]

Primary NOVA / brief voice is anna (female). Legal seat→voice map:
  brief=anna  hearth=anna  tutor=jane  deleo=michael
  sentinel=javert  chronicler=charles  reviewer=george
  seer=anna  ear=javert  openclaw=michael  qwen=george  clerk=anna

Also legal (same meaning):
  [NOTICE brief] Status clear. [/NOTICE]
  SPEAK:brief:Status clear.
  **speak anna** Status clear.

Rules:
- Visible answer OUTSIDE the tag; spoken line INSIDE the tag.
- ONE spoken sentence, under 12 words. No JSON. No tool calls. No markdown fences wrapping the tag.
- Prefer seat name brief (maps to anna) or voice anna directly.
- If nothing to announce, emit zero speak tags.

Example:
Holmes finished. Seven probes green.
[speak anna] Sweep clean. [/speak]
"""


GRAMMAR_V2 = """
SPEECH RULES:
Speak only when Voice in SELF is UP and there is real news to announce. Then add ONE line after the visible answer:
[speak anna] <one short sentence of your own, under 12 words> [/speak]
Never copy the placeholder. Voice anna = brief seat.
Zero speak tags for refusals, unknowns, proposals, capability or status answers, or when Voice is DOWN/unknown.
Visible answer outside the tag. No JSON, no tool calls.
"""


def peel(text: str) -> tuple[str, list[tuple[str, str]]]:
    spoken: list[tuple[str, str]] = []
    out = text or ""
    for rx in (SPEAK_BLOCK, SPEAK_LINE, SPEAK_MD, SPEAK_COLON, SPEAK_XML):
        for m in rx.finditer(out):
            spoken.append((m.group(1).lower(), m.group(2).strip()))
        out = rx.sub("", out)
    cleaned = []
    for voice, line in spoken:
        line = re.sub(r"\s+", " ", line).strip().strip('"').strip("'")
        if line:
            cleaned.append((pocket.resolve_voice(voice), line[:180]))
    return re.sub(r"\n{3,}", "\n\n", out).strip(), cleaned
