"""Channel constants and upload defaults. Secrets come from environment variables only."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT_DIR / "outputs"
STATE_DIR = ROOT_DIR / "state"
LOG_CSV_PATH = STATE_DIR / "log.csv"
TOKENS_PATH = STATE_DIR / "tokens.json"

# --- Channel ---
CHANNEL_HANDLE = "@zenoknows100much"
CHANNEL_URL = "https://www.youtube.com/@zenoknows100much/shorts"

# --- Anthropic ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# --- HeyGen (legacy — used if DID_API_KEY is not set) ---
HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY", "")
HEYGEN_AVATAR_ID = os.environ.get("HEYGEN_AVATAR_ID", "")
HEYGEN_VOICE_ID = os.environ.get("HEYGEN_VOICE_ID", "")
# avatar_iv | avatar_v | avatar_iii — must match what your avatar/plan supports.
HEYGEN_ENGINE = os.environ.get("HEYGEN_ENGINE", "avatar_iv")
HEYGEN_POLL_INTERVAL_SECONDS = 20
HEYGEN_POLL_TIMEOUT_SECONDS = 20 * 60

# --- D-ID (preferred video backend — set DID_API_KEY to activate) ---
# Cheaper than HeyGen (~$0.25/Short on Lite plan) and accepts any face image,
# enabling a different real historical figure per video rather than a fixed avatar.
# Auth: D-ID uses Basic auth with your API key — get it from studio.d-id.com/settings.
# Verify voice IDs at https://docs.d-id.com/reference/get_tts-voices
DID_API_KEY = os.environ.get("DID_API_KEY", "")
DID_TTS_PROVIDER = os.environ.get("DID_TTS_PROVIDER", "microsoft")
DID_TTS_VOICE_ID = os.environ.get("DID_TTS_VOICE_ID", "en-US-GuyNeural")
DID_POLL_INTERVAL_SECONDS = 5
DID_POLL_TIMEOUT_SECONDS = 10 * 60
# Fallback image URL used when Wikipedia cannot find a headshot for the persona.
DID_FALLBACK_IMAGE_URL = os.environ.get("DID_FALLBACK_IMAGE_URL", "")

# --- YouTube ---
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN_ENV = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs

# Decided once, hardcoded: this channel's content is not child-directed.
MADE_FOR_KIDS = False

# Videos publish public immediately (no private/unlisted holding period).
PRIVACY_STATUS = "public"

# --- Script constraints ---
TARGET_DURATION_SECONDS = (20, 32)
TOPIC_SEED = os.environ.get("TOPIC_SEED", "")

# --- Captions (rolling, per-word-highlighted karaoke style) ---
CAPTION_WHISPER_MODEL = os.environ.get("CAPTION_WHISPER_MODEL", "base.en")
CAPTION_HIGHLIGHT_COLOR = os.environ.get("CAPTION_HIGHLIGHT_COLOR", "#FFE600")  # bright yellow
CAPTION_WORDS_PER_LINE = int(os.environ.get("CAPTION_WORDS_PER_LINE", "3"))
CAPTION_FONT = os.environ.get("CAPTION_FONT", "Impact")
CAPTION_FONT_SIZE = int(os.environ.get("CAPTION_FONT_SIZE", "80"))
CAPTION_OUTLINE_WIDTH = int(os.environ.get("CAPTION_OUTLINE_WIDTH", "5"))
CAPTION_MARGIN_V = int(os.environ.get("CAPTION_MARGIN_V", "160"))
CAPTION_VIDEO_WIDTH = 720
CAPTION_VIDEO_HEIGHT = 1280

# --- Notifications (email via SMTP) ---
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
NOTIFY_EMAIL_FROM = os.environ.get("NOTIFY_EMAIL_FROM", "") or SMTP_USERNAME
NOTIFY_EMAIL_TO = os.environ.get("NOTIFY_EMAIL_TO", "")
