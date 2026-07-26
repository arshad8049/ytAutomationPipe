"""Claude API -> Short script + upload metadata, returned as strict JSON."""
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
hosted by an energetic AI avatar character named Zeno. Style: high-energy, hook in the first \
line, simple vocabulary, one clear idea per Short, a punchy closing line. No profanity, no \
adult themes, no medical/legal/financial advice.

The script must read aloud in {min_s}-{max_s} seconds (roughly 75-115 spoken words).

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
                "description": "YouTube title, under 100 characters, include #Shorts.",
            },
            "description": {
                "type": "string",
                "description": "YouTube description, 1-3 sentences, include #Shorts.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 5,
                "maxItems": 15,
                "description": "5-15 relevant YouTube tags, no leading # or spaces.",
            },
        },
        "required": ["script", "title", "description", "tags"],
    },
}


def generate_script(topic: str | None = None) -> dict:
    """Calls Claude and returns {"script", "title", "description", "tags"}.

    Retries once on a schema-valid-but-content-invalid response (e.g. Claude
    returning an empty tags array) since tool_choice guarantees the shape of
    the call but not that fields like minItems get honored.
    """
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    chosen_topic = topic or config.TOPIC_SEED or random.choice(_TOPIC_ROTATION)
    min_s, max_s = config.TARGET_DURATION_SECONDS

    last_error: Exception | None = None
    for _attempt in range(2):
        message = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT.format(min_s=min_s, max_s=max_s),
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "emit_short"},
            messages=[
                {
                    "role": "user",
                    "content": f"Today's Short topic: {chosen_topic}",
                }
            ],
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


if __name__ == "__main__":
    import json

    print(json.dumps(generate_script(), indent=2))
