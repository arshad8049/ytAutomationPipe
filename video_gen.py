"""Submit a script to HeyGen, poll until done, download the resulting mp4.

Verify endpoint paths/fields against HeyGen's current docs (app.heygen.com/settings ->
API) before relying on this in production; their API surface has changed shape before.
"""
import time
from pathlib import Path

import requests

import config

_BASE_URL = "https://api.heygen.com"
_PORTRAIT_DIMENSIONS = {"width": 720, "height": 1280}  # 9:16 for Shorts


class VideoGenError(RuntimeError):
    pass


def _headers() -> dict:
    return {"X-Api-Key": config.HEYGEN_API_KEY, "Content-Type": "application/json"}


def submit_job(script_text: str) -> str:
    """Submits a generation job, returns the HeyGen video_id."""
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": config.HEYGEN_AVATAR_ID,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script_text,
                    "voice_id": config.HEYGEN_VOICE_ID,
                },
            }
        ],
        "dimension": _PORTRAIT_DIMENSIONS,
        "test": False,
    }
    resp = requests.post(f"{_BASE_URL}/v2/video/generate", json=payload, headers=_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    video_id = data.get("data", {}).get("video_id")
    if not video_id:
        raise VideoGenError(f"HeyGen submit response missing video_id: {data}")
    return video_id


def poll_until_done(video_id: str) -> str:
    """Polls status until completed, returns the downloadable video_url. Raises on failure/timeout."""
    deadline = time.monotonic() + config.HEYGEN_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        resp = requests.get(
            f"{_BASE_URL}/v1/video_status.get",
            params={"video_id": video_id},
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        status = data.get("status")

        if status == "completed":
            video_url = data.get("video_url")
            if not video_url:
                raise VideoGenError(f"HeyGen reported completed but no video_url: {data}")
            return video_url
        if status == "failed":
            raise VideoGenError(f"HeyGen job {video_id} failed: {data.get('error')}")

        time.sleep(config.HEYGEN_POLL_INTERVAL_SECONDS)

    raise VideoGenError(f"HeyGen job {video_id} timed out after {config.HEYGEN_POLL_TIMEOUT_SECONDS}s")


def download(video_url: str, dest_path: Path) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(video_url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return dest_path


def generate_video(script_text: str, dest_path: Path) -> Path:
    """Submit + poll + download, with a single retry if the first attempt fails."""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            video_id = submit_job(script_text)
            video_url = poll_until_done(video_id)
            return download(video_url, dest_path)
        except (VideoGenError, requests.RequestException) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(5)
                continue
    raise VideoGenError(f"video_gen failed after retry: {last_error}") from last_error
