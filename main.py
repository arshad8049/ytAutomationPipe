"""Daily orchestration: script -> video -> upload -> log -> notify."""
import argparse
import csv
import datetime as dt
import sys

import captions
import config
import notify
import script_gen
import video_gen
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


def run(topic: str | None = None, cta: str | None = None) -> int:
    today = dt.date.today().isoformat()
    mode_note = "manual injection" if (topic or cta) else ""

    try:
        metadata = script_gen.generate_script(topic=topic, cta=cta)
    except Exception as exc:
        _append_log({"date": today, "title": "", "video_id": "", "url": "", "status": "failed", "detail": f"script_gen: {exc}"})
        notify.notify(f"Zeno Shorts FAILED — script_gen ({today})", str(exc))
        return 1

    title = metadata["title"]
    raw_video_path = config.OUTPUTS_DIR / f"{today}_raw.mp4"
    captioned_video_path = config.OUTPUTS_DIR / f"{today}.mp4"

    try:
        video_gen.generate_video(metadata["script"], raw_video_path)
    except Exception as exc:
        _append_log({"date": today, "title": title, "video_id": "", "url": "", "status": "failed", "detail": f"video_gen: {exc}"})
        notify.notify(f"Zeno Shorts FAILED — video_gen ({today})", f"'{title}': {exc}")
        return 1

    try:
        captions.add_karaoke_captions(raw_video_path, captioned_video_path)
    except Exception as exc:
        _append_log({"date": today, "title": title, "video_id": "", "url": "", "status": "failed", "detail": f"captions: {exc}"})
        notify.notify(f"Zeno Shorts FAILED — captions ({today})", f"'{title}': {exc}")
        return 1

    try:
        result = youtube_upload.upload_short(
            captioned_video_path, title, metadata["description"], metadata["tags"]
        )
    except Exception as exc:
        _append_log({"date": today, "title": title, "video_id": "", "url": "", "status": "failed", "detail": f"youtube_upload: {exc}"})
        notify.notify(f"Zeno Shorts FAILED — youtube_upload ({today})", f"'{title}': {exc}")
        return 1

    _append_log(
        {
            "date": today,
            "title": title,
            "video_id": result["video_id"],
            "url": result["url"],
            "status": "success",
            "detail": mode_note,
        }
    )
    notify.notify(f"Zeno Shorts published: {title}", f"{result['url']}\n\n{today}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Zeno Shorts daily pipeline.")
    parser.add_argument(
        "--topic",
        default=None,
        help="Override today's auto-picked topic with a specific one (manual injection mode).",
    )
    parser.add_argument(
        "--cta",
        default=None,
        help="Point the script's closing line at this, e.g. a specific main video to divert viewers to.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(run(topic=args.topic or None, cta=args.cta or None))
