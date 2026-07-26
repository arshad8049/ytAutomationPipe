"""Refresh-token OAuth auth + upload via YouTube Data API v3 videos.insert."""
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config

_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _load_refresh_token() -> str:
    if config.YOUTUBE_REFRESH_TOKEN_ENV:
        return config.YOUTUBE_REFRESH_TOKEN_ENV
    if config.TOKENS_PATH.exists():
        return json.loads(config.TOKENS_PATH.read_text())["refresh_token"]
    raise RuntimeError(
        "No YouTube refresh token found. Set YOUTUBE_REFRESH_TOKEN in .env or run "
        "auth/get_refresh_token.py once to generate state/tokens.json."
    )


def _get_client():
    creds = Credentials(
        token=None,
        refresh_token=_load_refresh_token(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.YOUTUBE_CLIENT_ID,
        client_secret=config.YOUTUBE_CLIENT_SECRET,
        scopes=_SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def upload_short(video_path: Path, title: str, description: str, tags: list[str]) -> dict:
    """Uploads video_path, returns {"video_id", "url"}."""
    youtube = _get_client()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": config.YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": config.PRIVACY_STATUS,
            "selfDeclaredMadeForKids": config.MADE_FOR_KIDS,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _status, response = request.next_chunk()

    video_id = response["id"]
    return {"video_id": video_id, "url": f"https://www.youtube.com/shorts/{video_id}"}
