# Zeno Knows — Automated YouTube Shorts Pipeline

A small end-to-end automation project that writes, generates, and publishes a YouTube
Short every day without any manual steps. I built this to explore chaining several APIs
(LLM, AI video generation, and the YouTube Data API) into a reliable, unattended
pipeline, with proper error handling and CI scheduling rather than a one-off script.

**Live channel:** [@zenoknows100much](https://www.youtube.com/@zenoknows100much/shorts)

## What it does

Once a day, a scheduled job:

1. **Writes a script** — calls the Anthropic API with a style/topic prompt and gets back
   strict, schema-validated JSON (script, title, description, tags), enforced with
   Claude's tool-use feature rather than hoping the model formats things correctly.
2. **Generates the video** — submits the script to HeyGen's avatar video API, polls the
   job until it's done, and downloads the finished MP4.
3. **Publishes it** — uploads to YouTube via the Data API v3 using OAuth2 refresh-token
   auth (no interactive login after the initial one-time setup), with metadata and
   compliance flags (like "Made for Kids") set explicitly rather than left to defaults.
4. **Logs and reports** — appends the result to a run log and pings a webhook
   (Slack/Discord) with the outcome, so failures are visible without checking in.

```
Scheduled trigger (GitHub Actions, daily)
        │
        ▼
1. Script generation   ──  Anthropic API  ──▶  script + title/description/tags (JSON)
        │
        ▼
2. Video generation     ──  HeyGen API  ──▶  submit job → poll → download .mp4
        │
        ▼
3. Upload                ──  YouTube Data API v3  ──▶  publish as a Short
        │
        ▼
4. Logging & alerting     ──  CSV log + webhook notification
```

Everything after the trigger fires runs unattended; I only step in if a step fails.

## Tech stack

- **Python** — orchestration and all API integrations
- **Anthropic API** — script + metadata generation, structured output via tool-use
- **HeyGen API** — AI avatar video rendering
- **YouTube Data API v3** — OAuth2 (refresh-token flow), video upload
- **GitHub Actions** — cron-based scheduling, no server to maintain
- **CSV logging + webhooks** — lightweight observability without a database

## Project layout

```
config.py                    channel constants, avatar ID, upload defaults
script_gen.py                 Claude → {script, title, description, tags}, strict JSON
video_gen.py                  HeyGen submit → poll → download, retries once on failure
youtube_upload.py             OAuth refresh-token auth → videos.insert
auth/get_refresh_token.py     one-time local consent flow to mint the refresh token
webhook.py                    Slack/Discord/generic run notifications
main.py                       runs the pipeline end to end, logs, exits non-zero on failure
.github/workflows/            daily scheduled run + manual trigger for testing
state/log.csv                 history of every run (date, title, video id, status)
```

## Design decisions worth calling out

- **Structured output over regex parsing** — the script generation step forces Claude to
  respond through a tool call with a defined JSON schema, so downstream steps never have
  to guess at parsing a loosely-formatted response.
- **Compliance set explicitly, not guessed** — YouTube requires an honest "Made for Kids"
  flag per video; rather than leaving that decision implicit, it's a config constant
  applied consistently to every upload.
- **Fail loudly, not silently** — every stage is wrapped so a failure is logged with
  context and pushed to a webhook, and the process exits non-zero so CI reflects the
  real state of the run.
- **No server required** — the whole thing runs on GitHub Actions' free scheduled
  workflows, which keeps the project self-contained and easy for anyone to fork and run
  with their own keys.

## Running it yourself

```bash
cd short_automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your own API keys — see below
```

You'll need your own keys for:
- **Anthropic** (console.anthropic.com)
- **HeyGen** (an API key plus an avatar/voice ID configured once in their dashboard)
- **YouTube Data API v3** (a Google Cloud project with the API enabled and an OAuth
  "Desktop app" client)
- Optionally, a **Slack or Discord webhook URL** for run notifications

### One-time YouTube authorization

```bash
python auth/get_refresh_token.py
```

This opens a browser for a one-time consent flow against your own channel, then stores a
refresh token locally so every future upload is fully unattended.

### Test before scheduling

```bash
python main.py
```

Check `state/log.csv` and the channel for the result. I'd suggest setting
`PRIVACY_STATUS = "unlisted"` in `config.py` for your first few runs until you trust the
output, then switching to `"public"`.

### Scheduling with GitHub Actions

Push the repo to GitHub, add your keys as repository secrets (Settings → Secrets and
variables → Actions, same names as in `.env`), and the included workflow takes it from
there — a daily cron trigger plus a manual `workflow_dispatch` option for testing.

## Known limitations / possible next steps

- HeyGen's endpoint shapes in `video_gen.py` are based on their documented API surface at
  the time of writing — worth a quick diff against current docs if their API changes.
- Run history currently lives in a CSV committed back to the repo by the workflow; a real
  database or spreadsheet integration would scale better past a few hundred runs.
- No automated content moderation pass before publish — currently relies on the prompt
  constraints plus the public/unlisted staging period.
