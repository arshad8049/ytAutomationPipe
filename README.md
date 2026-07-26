# Zeno Knows — Daily Shorts Automation

Target channel: https://www.youtube.com/@zenoknows100much/shorts

One Short a day, fully unattended after setup: Claude writes the script -> HeyGen renders
the avatar video -> it uploads to YouTube -> the run is logged and you get a webhook ping.

Locked-in decisions for this project (see `config.py` to change them):
- Video provider: **HeyGen**
- Scheduler: **GitHub Actions** (`.github/workflows/daily-short.yml`)
- `MADE_FOR_KIDS = False` — this channel's content is not child-directed
- `PRIVACY_STATUS = "public"` — videos go live immediately; you still get a webhook
  notification after each upload so you can catch a bad run after the fact

## 1. Local setup

```bash
cd short_automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `ANTHROPIC_API_KEY` — console.anthropic.com
- `HEYGEN_API_KEY`, `HEYGEN_AVATAR_ID`, `HEYGEN_VOICE_ID` — HeyGen dashboard, avatar set up once
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` — see step 2
- `WEBHOOK_URL` (+ `WEBHOOK_FORMAT`) — a Slack or Discord incoming webhook URL

## 2. One-time YouTube OAuth flow

1. In [console.cloud.google.com](https://console.cloud.google.com), create/select a project,
   enable **YouTube Data API v3**.
2. Create OAuth credentials of type **Desktop app**. Copy the client ID/secret into `.env`.
3. Run the local consent flow, signed in with the Google account that **owns**
   `@zenoknows100much` (double check this before authorizing — YouTube uploads go to
   whichever account approves the consent screen):

   ```bash
   python auth/get_refresh_token.py
   ```

   This opens a browser, asks for consent, then writes `state/tokens.json` and prints the
   refresh token. It doesn't expire unless revoked, so this is a one-time step.

## 3. Try it manually before scheduling anything

```bash
python main.py
```

Check `state/log.csv` and the channel for the result. Since `PRIVACY_STATUS` is `public`,
the first real run does go live — consider temporarily setting `PRIVACY_STATUS = "unlisted"`
in `config.py` for your first test run, then switching back once you're confident in output
quality.

## 4. Wire up GitHub Actions

1. Push this repo to GitHub.
2. In the repo's **Settings -> Secrets and variables -> Actions**, add each of these as a
   repository secret (same names as in `.env`):
   `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `HEYGEN_API_KEY`, `HEYGEN_AVATAR_ID`,
   `HEYGEN_VOICE_ID`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`,
   `WEBHOOK_URL`, `WEBHOOK_FORMAT`, `TOPIC_SEED` (optional).
3. The workflow runs daily at 14:00 UTC and also supports manual triggering from the
   **Actions** tab (`workflow_dispatch`) — use that to test end-to-end before trusting the
   schedule.
4. The workflow commits `state/log.csv` back to the repo after each run so history persists
   across ephemeral runners.

## Files

```
config.py           channel constants, avatar ID, upload defaults (made-for-kids, privacy)
script_gen.py        Claude -> {script, title, description, tags} via forced tool-use JSON
video_gen.py         HeyGen submit -> poll -> download, one retry on failure
youtube_upload.py    refresh-token OAuth -> videos.insert
auth/get_refresh_token.py   one-time local consent flow
webhook.py           Slack/Discord/generic notification
main.py              runs the above in order, logs to state/log.csv, exits non-zero on failure
state/log.csv        date, title, video_id, url, status, detail
state/tokens.json    stored refresh token (gitignored)
outputs/             generated mp4s land here temporarily
```

## Notes / things worth verifying before fully trusting this

- HeyGen's API fields (`video_gen.py`) were written against their documented `v2/video/generate`
  and `v1/video_status.get` shape — confirm against your HeyGen dashboard's current API docs,
  since third-party APIs do change.
- YouTube infers "Shorts" from vertical aspect ratio (this pipeline renders 720x1280) plus
  duration under ~3 minutes; Claude is prompted to include `#Shorts` in the title/description
  as an extra signal.
- Re-confirm the Google account used in the one-time OAuth flow is the one that actually owns
  `@zenoknows100much` — uploads go to whichever account granted consent.
