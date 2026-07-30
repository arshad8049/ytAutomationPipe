"""Generate a talking-head video via D-ID's /talks API.

D-ID accepts a source image URL + a text script (with built-in TTS), renders the video
server-side, then returns a download URL. Much cheaper than HeyGen (~$0.25/Short on their
Lite plan) and accepts any publicly accessible face image — so each Short features the
actual historical figure it's about.

Auth: D-ID uses HTTP Basic auth. Your API key from studio.d-id.com/settings goes directly
in the Authorization header as "Basic <key>". No base64 encoding of email:password needed —
D-ID issues a pre-encoded credential string.

API reference: https://docs.d-id.com/reference/createtalk
"""
import time
from pathlib import Path

import requests

import config


class DIDError(RuntimeError):
    pass


_BASE_URL = "https://api.d-id.com"


def _headers() -> dict:
    return {
        "Authorization": f"Basic {config.DID_API_KEY}",
        "Content-Type": "application/json",
    }


def _create_talk(script_text: str, source_image_url: str) -> str:
    payload = {
        "source_url": source_image_url,
        "script": {
            "type": "text",
            "input": script_text,
            "provider": {
                "type": config.DID_TTS_PROVIDER,
                "voice_id": config.DID_TTS_VOICE_ID,
            },
        },
        "config": {"result_format": "mp4"},
    }
    resp = requests.post(f"{_BASE_URL}/talks", json=payload, headers=_headers(), timeout=30)
    resp.raise_for_status()
    talk_id = resp.json().get("id")
    if not talk_id:
        raise DIDError(f"D-ID submit missing id: {resp.json()}")
    return talk_id


def _poll_until_done(talk_id: str) -> str:
    deadline = time.monotonic() + config.DID_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        resp = requests.get(f"{_BASE_URL}/talks/{talk_id}", headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "done":
            url = data.get("result_url")
            if not url:
                raise DIDError(f"D-ID done but no result_url: {data}")
            return url
        if status == "error":
            raise DIDError(f"D-ID talk {talk_id} failed: {data.get('error')}")
        time.sleep(config.DID_POLL_INTERVAL_SECONDS)
    raise DIDError(f"D-ID talk {talk_id} timed out after {config.DID_POLL_TIMEOUT_SECONDS}s")


def _download(video_url: str, dest_path: Path) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(video_url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return dest_path


def generate_video(script_text: str, source_image_url: str, dest_path: Path) -> Path:
    """Full D-ID pipeline: submit → poll → download → dest_path.

    source_image_url must be a publicly accessible URL (Wikimedia URLs work directly).
    Billed on submission — does not retry with a new job on transient errors, for the
    same reason as the HeyGen implementation: resubmitting risks paying twice for a
    render that may have already completed.
    """
    talk_id = _create_talk(script_text, source_image_url)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            video_url = _poll_until_done(talk_id)
            return _download(video_url, dest_path)
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(5)
                continue
    raise DIDError(f"video_gen_did failed after retry (talk_id={talk_id}): {last_error}") from last_error
