"""Post a run result to a Slack/Discord/generic webhook."""
import requests

import config


def notify(text: str) -> None:
    if not config.WEBHOOK_URL:
        return

    if config.WEBHOOK_FORMAT == "slack":
        payload = {"text": text}
    elif config.WEBHOOK_FORMAT == "discord":
        payload = {"content": text}
    else:
        payload = {"message": text}

    try:
        requests.post(config.WEBHOOK_URL, json=payload, timeout=15)
    except requests.RequestException as exc:
        print(f"webhook notify failed: {exc}")
