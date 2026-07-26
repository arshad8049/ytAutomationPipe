"""Burn karaoke-style captions into a rendered video: the word currently being
spoken is highlighted in a different color, in a rolling line of a few words.

Done as a local post-processing step (faster-whisper for word timing + ffmpeg for
burn-in) rather than relying on HeyGen's own caption styling, since HeyGen's public
API docs don't clearly document whether karaoke-highlight coloring is controllable
there (vs. only in their web editor) — guessing wrong would waste a billed render.
This way is also fully under our control for the exact highlight color.
"""
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel

import config

_model: WhisperModel | None = None


class CaptionError(RuntimeError):
    pass


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(config.CAPTION_WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def _transcribe_words(video_path: Path) -> list[dict]:
    """Returns [{"word", "start", "end"}, ...] timed against the video's own audio."""
    segments, _info = _get_model().transcribe(str(video_path), word_timestamps=True)
    words = []
    for segment in segments:
        for w in segment.words:
            words.append({"word": w.word.strip(), "start": w.start, "end": w.end})
    if not words:
        raise CaptionError("transcription returned no words — is the video silent?")
    return words


def _chunk_words(words: list[dict], size: int) -> list[list[dict]]:
    return [words[i : i + size] for i in range(0, len(words), size)]


def _hex_to_ass_bgr(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def _escape_ass_filter_path(path: Path) -> str:
    # ffmpeg's filtergraph parser treats ':' and '\' specially in filter option values.
    return str(path).replace("\\", "\\\\").replace(":", "\\:")


_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,{outline},0,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ass_timestamp(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    cs = round(seconds * 100)
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _build_ass(words: list[dict], dest_path: Path) -> None:
    highlight = _hex_to_ass_bgr(config.CAPTION_HIGHLIGHT_COLOR)
    chunks = _chunk_words(words, config.CAPTION_WORDS_PER_LINE)

    lines = [
        _ASS_HEADER.format(
            width=config.CAPTION_VIDEO_WIDTH,
            height=config.CAPTION_VIDEO_HEIGHT,
            font=config.CAPTION_FONT,
            font_size=config.CAPTION_FONT_SIZE,
            outline=config.CAPTION_OUTLINE_WIDTH,
            margin_v=config.CAPTION_MARGIN_V,
        )
    ]

    for chunk in chunks:
        plain_words = [w["word"] for w in chunk]
        for i, active in enumerate(chunk):
            text = " ".join(
                f"{{\\c{highlight}}}{w}{{\\r}}" if j == i else w
                for j, w in enumerate(plain_words)
            )
            start, end = _ass_timestamp(active["start"]), _ass_timestamp(active["end"])
            lines.append(f"Dialogue: 0,{start},{end},Caption,,0,0,0,,{text}\n")

    dest_path.write_text("".join(lines))


def add_karaoke_captions(video_path: Path, dest_path: Path) -> Path:
    """Transcribes video_path's own audio for word timing, then burns in rolling,
    per-word-highlighted captions, writing the result to dest_path."""
    words = _transcribe_words(video_path)

    ass_path = dest_path.with_suffix(".ass")
    _build_ass(words, ass_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"ass={_escape_ass_filter_path(ass_path)}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(dest_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise CaptionError(f"ffmpeg caption burn-in failed: {result.stderr[-2000:]}")

    return dest_path
