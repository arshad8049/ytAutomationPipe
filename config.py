"""Channel constants and upload defaults. Secrets come from environment variables only."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    # GitHub Actions passes an unset secret as an empty string, which would
    # otherwise defeat os.environ.get() defaults — treat "" as unset.
    return os.environ.get(name) or default


ROOT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT_DIR / "outputs"
STATE_DIR = ROOT_DIR / "state"
LOG_CSV_PATH = STATE_DIR / "log.csv"
TOKENS_PATH = STATE_DIR / "tokens.json"

# --- Channel ---
CHANNEL_HANDLE = "@zenoknows100much"
CHANNEL_URL = "https://www.youtube.com/@zenoknows100much/shorts"

# --- Anthropic ---
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = _env("CLAUDE_MODEL", "claude-sonnet-4-6")

# --- HeyGen (legacy — used if DID_API_KEY is not set) ---
HEYGEN_API_KEY = _env("HEYGEN_API_KEY", "")
HEYGEN_AVATAR_ID = _env("HEYGEN_AVATAR_ID", "")
HEYGEN_VOICE_ID = _env("HEYGEN_VOICE_ID", "")
# avatar_iv | avatar_v | avatar_iii — must match what your avatar/plan supports.
HEYGEN_ENGINE = _env("HEYGEN_ENGINE", "avatar_iv")
HEYGEN_POLL_INTERVAL_SECONDS = 20
HEYGEN_POLL_TIMEOUT_SECONDS = 20 * 60

# --- D-ID (preferred video backend — set DID_API_KEY to activate) ---
# Cheaper than HeyGen (~$0.25/Short on Lite plan) and accepts any face image,
# enabling a different real historical figure per video rather than a fixed avatar.
# Auth: D-ID uses Basic auth with your API key — get it from studio.d-id.com/settings.
# Verify voice IDs at https://docs.d-id.com/reference/get_tts-voices
DID_API_KEY = _env("DID_API_KEY", "")
DID_TTS_PROVIDER = _env("DID_TTS_PROVIDER", "microsoft")
DID_TTS_VOICE_ID = _env("DID_TTS_VOICE_ID", "en-US-GuyNeural")
DID_POLL_INTERVAL_SECONDS = 5
DID_POLL_TIMEOUT_SECONDS = 10 * 60
# Fallback image URL used when Wikipedia cannot find a headshot for the persona.
DID_FALLBACK_IMAGE_URL = _env("DID_FALLBACK_IMAGE_URL", "")

# --- YouTube ---
YOUTUBE_CLIENT_ID = _env("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = _env("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN_ENV = _env("YOUTUBE_REFRESH_TOKEN", "")
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs

# Decided once, hardcoded: this channel's content is not child-directed.
MADE_FOR_KIDS = False

# Videos publish public immediately (no private/unlisted holding period).
PRIVACY_STATUS = "public"

# --- Script constraints ---
TARGET_DURATION_SECONDS = (20, 32)
TOPIC_SEED = _env("TOPIC_SEED", "")

# --- Captions (rolling, per-word-highlighted karaoke style) ---
CAPTION_WHISPER_MODEL = _env("CAPTION_WHISPER_MODEL", "base.en")
CAPTION_HIGHLIGHT_COLOR = _env("CAPTION_HIGHLIGHT_COLOR", "#FFE600")  # bright yellow
CAPTION_WORDS_PER_LINE = int(_env("CAPTION_WORDS_PER_LINE", "3"))
CAPTION_FONT = _env("CAPTION_FONT", "Impact")
CAPTION_FONT_SIZE = int(_env("CAPTION_FONT_SIZE", "80"))
CAPTION_OUTLINE_WIDTH = int(_env("CAPTION_OUTLINE_WIDTH", "5"))
CAPTION_MARGIN_V = int(_env("CAPTION_MARGIN_V", "160"))
CAPTION_VIDEO_WIDTH = 720
CAPTION_VIDEO_HEIGHT = 1280

# --- Notifications (email via SMTP) ---
SMTP_HOST = _env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_env("SMTP_PORT", "587"))
SMTP_USERNAME = _env("SMTP_USERNAME", "")
SMTP_PASSWORD = _env("SMTP_PASSWORD", "")
NOTIFY_EMAIL_FROM = _env("NOTIFY_EMAIL_FROM", "") or SMTP_USERNAME
NOTIFY_EMAIL_TO = _env("NOTIFY_EMAIL_TO", "")
