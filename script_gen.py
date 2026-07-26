"""Claude API -> Short script + upload metadata, returned as strict JSON.

Prompted for two things at once: a script that's actually worth finishing (hook in
the first ~1 second, one idea, no throat-clearing), and metadata tuned to how YouTube
Shorts discovery actually works — keyword-first titles, a focused (not bloated) tag
list, and hashtag placement that becomes clickable above the title.
"""
import random

from anthropic import Anthropic

import config

_TOPIC_ROTATION = [
    "a mind-blowing AI-for-kids fact explained simply",
    "a current brainrot/internet trend recapped and explained",
    "a weird-but-true science fact",
    "a quick life hack or riddle with a payoff",
    "a fun history fact retold with a twist",
]

_SYSTEM_PROMPT = """You write scripts for "Zeno Knows", a fast, punchy YouTube Shorts channel \
hosted by an energetic AI avatar character named Zeno. No profanity, no adult themes, no \
medical/legal/financial advice.

SCRIPT — must be genuinely worth watching to the end, not just short:
- Open with a pattern interrupt or curiosity gap in the FIRST sentence — a claim, question, or \
  visual that makes stopping the scroll feel costly. Never open with "Hey guys", "Today we're \
  talking about", or any other throat-clearing; start mid-thought, as if already answering the \
  hook.
- One idea per Short. Cut anything that doesn't serve the hook's payoff.
- Simple, spoken vocabulary — this is read aloud by a TTS avatar, not read on screen.
- Close with either a tight payoff/twist that rewards a rewatch, or a natural line that sets up \
  tomorrow's topic — never a flat summary restating what was just said.
- Must read aloud in {min_s}-{max_s} seconds (roughly {min_w}-{max_w} spoken words). This is a \
  hard budget, not a suggestion — going over both costs more to render and hurts watch-through \
  rate, which is what YouTube's algorithm uses to decide whether to push a Short further.

METADATA — optimized for how Shorts discovery actually ranks, not just keyword-stuffed:
- title: put the core keyword/topic in the first 3 words, state the payoff, sound like a human \
  wrote it. Under 100 characters. Do not put hashtags in the title.
- description: 1-3 sentences of genuine, keyword-rich context (not a repeat of the title), \
  followed by 3-5 hashtags with #Shorts listed FIRST — YouTube renders the first 3 hashtags in \
  a description as clickable links above the title, so order matters. Never exceed 5 hashtags.
- tags: 8-12 tags. Focused and specific beats bloated — a tight, accurate list holds more \
  algorithmic confidence about the video's subject than a maxed-out list of loosely related \
  terms. No leading # or extra spaces.

Respond only by calling the `emit_short` tool. Do not include any other text."""

_TOOL_SCHEMA = {
    "name": "emit_short",
    "description": "Emit the finished Short script and its YouTube upload metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "The full spoken script, ready to hand to a text-to-speech avatar.",
            },
            "title": {
                "type": "string",
                "description": "YouTube title, keyword in the first 3 words, under 100 characters, no hashtags.",
            },
            "description": {
                "type": "string",
                "description": (
                    "YouTube description: 1-3 sentences of real context, then 3-5 hashtags "
                    "with #Shorts first."
                ),
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 8,
                "maxItems": 12,
                "description": "8-12 focused, relevant YouTube tags, no leading # or spaces.",
            },
        },
        "required": ["script", "title", "description", "tags"],
    },
}

# Hard ceiling on script length, independent of the prompt's target — protects against
# a runaway generation turning into an expensive HeyGen render (billed per second).
_MAX_SCRIPT_WORDS = 130


def generate_script(topic: str | None = None, cta: str | None = None) -> dict:
    """Calls Claude and returns {"script", "title", "description", "tags"}.

    `cta` is for manual-injection runs: a short note on what today's Short should point
    viewers toward (e.g. a longer video), worked into the script's closing line.

    Retries once on a schema-valid-but-content-invalid response (e.g. Claude returning
    an empty tags array, or a script that blows past the length budget) since tool_choice
    guarantees the shape of the call but not that fields like minItems/length get honored.
    """
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    chosen_topic = topic or config.TOPIC_SEED or random.choice(_TOPIC_ROTATION)
    min_s, max_s = config.TARGET_DURATION_SECONDS
    min_w, max_w = int(min_s * 2.5), int(max_s * 2.5)  # ~150 wpm spoken pace

    user_content = f"Today's Short topic: {chosen_topic}"
    if cta:
        user_content += (
            f"\n\nThis Short needs to drive viewers toward: {cta}\n"
            "Close the script with one natural, in-voice line pointing them there "
            '(e.g. "Full story\'s on the channel") — no hard sales pitch, no breaking '
            "character."
        )

    last_error: Exception | None = None
    for _attempt in range(2):
        message = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT.format(min_s=min_s, max_s=max_s, min_w=min_w, max_w=max_w),
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "emit_short"},
            messages=[{"role": "user", "content": user_content}],
        )

        result = None
        for block in message.content:
            if block.type == "tool_use" and block.name == "emit_short":
                result = dict(block.input)
                break

        if result is None:
            last_error = RuntimeError("Claude did not return an emit_short tool call")
            continue

        try:
            _normalize_tags(result)
            _validate(result)
            return result
        except ValueError as exc:
            last_error = exc

    raise last_error


def _normalize_tags(result: dict) -> None:
    """Claude's tool-use schema isn't strictly type-enforced; it sometimes returns
    tags as a single comma-separated string instead of a JSON array. Coerce it."""
    tags = result.get("tags")
    if isinstance(tags, str):
        result["tags"] = [t.strip().lstrip("#") for t in tags.split(",") if t.strip()]


def _validate(result: dict) -> None:
    required = ("script", "title", "description", "tags")
    missing = [key for key in required if key not in result]
    if missing:
        raise ValueError(f"script_gen result missing keys: {missing}")
    if not isinstance(result["tags"], list) or not result["tags"]:
        raise ValueError("script_gen result 'tags' must be a non-empty list")

    word_count = len(result["script"].split())
    if word_count > _MAX_SCRIPT_WORDS:
        raise ValueError(
            f"script_gen script is {word_count} words, over the {_MAX_SCRIPT_WORDS}-word "
            "cost/pacing ceiling"
        )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Generate one Short's script + metadata.")
    parser.add_argument("--topic", help="Override today's auto-picked topic.")
    parser.add_argument("--cta", help="Point the script's closing line at this (e.g. a main video).")
    args = parser.parse_args()

    print(json.dumps(generate_script(topic=args.topic, cta=args.cta), indent=2))
