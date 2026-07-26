"""Email a run result via SMTP."""
import smtplib
from email.mime.text import MIMEText

import config


def notify(subject: str, body: str) -> None:
    if not (config.SMTP_USERNAME and config.SMTP_PASSWORD and config.NOTIFY_EMAIL_TO):
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.NOTIFY_EMAIL_FROM
    msg["To"] = config.NOTIFY_EMAIL_TO

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.sendmail(config.NOTIFY_EMAIL_FROM, [config.NOTIFY_EMAIL_TO], msg.as_string())
    except (smtplib.SMTPException, OSError) as exc:
        print(f"email notify failed: {exc}")
