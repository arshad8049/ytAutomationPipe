"""Submit a script to HeyGen, poll until done, download the resulting mp4.

Uses HeyGen's v3 API (POST /v3/videos, GET /v3/videos/{id}) — the older v2 endpoint
this used to target is deprecated and scheduled for removal 2026-10-31. Verify against
developers.heygen.com/reference/create-video before relying on this in production;
their API surface has changed shape before.
"""
import time
from pathlib import Path

import requests

import config

_BASE_URL = "https://api.heygen.com"


class VideoGenError(RuntimeError):
    pass


def _headers() -> dict:
    return {"x-api-key": config.HEYGEN_API_KEY, "Content-Type": "application/json"}


def _unwrap(payload: dict) -> dict:
    """v3 responses observed to wrap the real body in {"data": ...}; be defensive
    in case a given response comes back unwrapped."""
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def submit_job(script_text: str) -> str:
    """Submits a generation job, returns the HeyGen video_id."""
    payload = {
        "type": "avatar",
        "avatar_id": config.HEYGEN_AVATAR_ID,
        "script": script_text,
        "voice_id": config.HEYGEN_VOICE_ID,
        "resolution": "720p",
        "aspect_ratio": "9:16",  # portrait, for Shorts
        "output_format": "mp4",
        "engine": {"type": config.HEYGEN_ENGINE},
    }
    resp = requests.post(f"{_BASE_URL}/v3/videos", json=payload, headers=_headers(), timeout=30)
    resp.raise_for_status()
    data = _unwrap(resp.json())
    video_id = data.get("video_id")
    if not video_id:
        raise VideoGenError(f"HeyGen submit response missing video_id: {data}")
    return video_id


def poll_until_done(video_id: str) -> str:
    """Polls status until completed, returns the downloadable video_url. Raises on failure/timeout."""
    deadline = time.monotonic() + config.HEYGEN_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        resp = requests.get(f"{_BASE_URL}/v3/videos/{video_id}", headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = _unwrap(resp.json())
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
    """Submits exactly one HeyGen job (billed on submission), then retries polling/
    download against that SAME job on transient network errors.

    Deliberately does not resubmit a fresh job on failure: HeyGen bills per render
    regardless of whether our poll/download step succeeds afterward, so retrying by
    resubmitting would silently double-charge for a render that may have already
    completed. A hard "failed" status or a timeout from poll_until_done is raised
    immediately rather than retried, since resubmitting wouldn't fix whatever made
    the render itself fail and would just risk paying twice.
    """
    video_id = submit_job(script_text)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            video_url = poll_until_done(video_id)
            return download(video_url, dest_path)
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(5)
                continue
    raise VideoGenError(f"video_gen failed after retry (video_id={video_id}): {last_error}") from last_error
