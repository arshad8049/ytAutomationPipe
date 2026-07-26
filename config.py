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
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

# --- HeyGen ---
HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY", "")
HEYGEN_AVATAR_ID = os.environ.get("HEYGEN_AVATAR_ID", "")
HEYGEN_VOICE_ID = os.environ.get("HEYGEN_VOICE_ID", "")
HEYGEN_POLL_INTERVAL_SECONDS = 20
HEYGEN_POLL_TIMEOUT_SECONDS = 20 * 60

# --- YouTube ---
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN_ENV = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs

# Decided once, hardcoded: this channel's content is not child-directed.
# Changing this per-video is exactly what YouTube's policy warns against guessing on.
MADE_FOR_KIDS = False

# Videos publish public immediately (no private/unlisted holding period).
PRIVACY_STATUS = "public"

# --- Script constraints ---
TARGET_DURATION_SECONDS = (30, 45)
TOPIC_SEED = os.environ.get("TOPIC_SEED", "")

# --- Notifications ---
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
WEBHOOK_FORMAT = os.environ.get("WEBHOOK_FORMAT", "slack")
