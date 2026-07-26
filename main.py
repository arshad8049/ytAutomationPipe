"""Daily orchestration: script -> video -> upload -> log -> notify."""
import csv
import datetime as dt
import sys

import config
import script_gen
import video_gen
import webhook
import youtube_upload

_LOG_FIELDS = ["date", "title", "video_id", "url", "status", "detail"]


def _append_log(row: dict) -> None:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not config.LOG_CSV_PATH.exists()
    with open(config.LOG_CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def run() -> int:
    today = dt.date.today().isoformat()

    try:
        metadata = script_gen.generate_script()
    except Exception as exc:
        _append_log({"date": today, "title": "", "video_id": "", "url": "", "status": "failed", "detail": f"script_gen: {exc}"})
        webhook.notify(f":x: Zeno Shorts run failed at script_gen ({today}): {exc}")
        return 1

    title = metadata["title"]
    video_path = config.OUTPUTS_DIR / f"{today}.mp4"

    try:
        video_gen.generate_video(metadata["script"], video_path)
    except Exception as exc:
        _append_log({"date": today, "title": title, "video_id": "", "url": "", "status": "failed", "detail": f"video_gen: {exc}"})
        webhook.notify(f":x: Zeno Shorts run failed at video_gen ({today}, '{title}'): {exc}")
        return 1

    try:
        result = youtube_upload.upload_short(
            video_path, title, metadata["description"], metadata["tags"]
        )
    except Exception as exc:
        _append_log({"date": today, "title": title, "video_id": "", "url": "", "status": "failed", "detail": f"youtube_upload: {exc}"})
        webhook.notify(f":x: Zeno Shorts run failed at youtube_upload ({today}, '{title}'): {exc}")
        return 1

    _append_log(
        {
            "date": today,
            "title": title,
            "video_id": result["video_id"],
            "url": result["url"],
            "status": "success",
            "detail": "",
        }
    )
    webhook.notify(f":white_check_mark: Zeno Shorts uploaded '{title}': {result['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
