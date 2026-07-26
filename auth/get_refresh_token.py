"""One-time local OAuth consent flow. Run this once to obtain a YouTube refresh token.

Usage:
    python auth/get_refresh_token.py

Requires YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env (OAuth client type
"Desktop app" from console.cloud.google.com). Opens a browser for you to sign in
with the Google account that OWNS the target channel, then writes the refresh
token to state/tokens.json.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

from google_auth_oauthlib.flow import InstalledAppFlow

import config

_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    if not config.YOUTUBE_CLIENT_ID or not config.YOUTUBE_CLIENT_SECRET:
        raise SystemExit("Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env first.")

    client_config = {
        "installed": {
            "client_id": config.YOUTUBE_CLIENT_ID,
            "client_secret": config.YOUTUBE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, _SCOPES)
    print("A browser window will open. Sign in with the Google account that owns")
    print(f"  {config.CHANNEL_URL}")
    print("and grant access.\n")
    credentials = flow.run_local_server(port=0)

    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    config.TOKENS_PATH.write_text(json.dumps({"refresh_token": credentials.refresh_token}, indent=2))

    print(f"\nSaved refresh token to {config.TOKENS_PATH}")
    print("For GitHub Actions, also copy this value into the YOUTUBE_REFRESH_TOKEN repo secret:")
    print(f"  {credentials.refresh_token}")


if __name__ == "__main__":
    main()
