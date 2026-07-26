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
4. **Logs and reports** — appends the result to a run log and emails me the outcome,
   so failures are visible without checking in.

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
4. Logging & alerting     ──  CSV log + email notification
```

Everything after the trigger fires runs unattended; I only step in if a step fails.

## Tech stack

- **Python** — orchestration and all API integrations
- **Anthropic API** — script + metadata generation, structured output via tool-use
- **HeyGen API** — AI avatar video rendering
- **YouTube Data API v3** — OAuth2 (refresh-token flow), video upload
- **GitHub Actions** — cron-based scheduling, no server to maintain
- **CSV logging + SMTP email** — lightweight observability without a database

## Project layout

```
config.py                    channel constants, avatar ID, upload defaults
script_gen.py                 Claude → {script, title, description, tags}, SEO-tuned, strict JSON
video_gen.py                  HeyGen v3 submit → poll → download, cost-safe retry
youtube_upload.py             OAuth refresh-token auth → videos.insert
auth/get_refresh_token.py     one-time local consent flow to mint the refresh token
notify.py                     SMTP email run notifications
main.py                       runs the pipeline end to end, supports manual topic/CTA injection
.github/workflows/            daily scheduled run + manual trigger, with optional topic/CTA inputs
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
  context and emailed out, and the process exits non-zero so CI reflects the real
  state of the run.
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
- Optionally, an **SMTP account** (e.g. a Gmail app password) for run-result emails

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

### Triggering a run manually from GitHub

Once secrets are set, no local machine is needed to run the pipeline on demand:

1. Go to the repo on GitHub → the **Actions** tab.
2. In the left sidebar, click **Daily Zeno Short**.
3. Click the **Run workflow** dropdown (top right of the run list).
4. Optionally fill in **topic** and/or **cta** (see Manual injection mode below), or leave
   both blank for a normal auto-picked run.
5. Click the green **Run workflow** button. A new run appears in a few seconds — click into
   it to watch each step's logs live.

Or from the command line with the [GitHub CLI](https://cli.github.com/):

```bash
gh workflow run daily-short.yml
# with an override:
gh workflow run daily-short.yml -f topic="a surprising fact about octopuses" -f cta="our full video on octopus intelligence"
```

### Manual injection mode

Normally the topic is auto-picked from a rotation. To steer a specific day's Short — most
usefully, to divert viewers toward a longer video — pass `--topic` and/or `--cta`:

```bash
python main.py --topic "a surprising fact about octopuses" \
               --cta "our full video 'Why Octopuses Are Basically Aliens' on the main channel"
```

`--topic` overrides what the Short is about; `--cta` gets woven into the script's closing
line as a natural pointer (not a hard sales pitch) toward whatever you name — typically a
longer video you want this Short acting as a teaser for. Either flag works alone. The same
two inputs are exposed on the GitHub Actions side (see above) so this doesn't require a
local machine either. Runs using either flag are tagged `manual injection` in `state/log.csv`.

## Cost and Shorts-algorithm notes

Two real constraints shaped `script_gen.py` and `video_gen.py`:

**HeyGen bills per second of rendered output**, so the pipeline is tuned to keep renders
short and to never accidentally pay twice for one:
- Script length target dropped from ~30-45s to ~20-32s (`config.TARGET_DURATION_SECONDS`) —
  cheaper to render, and shorter Shorts also tend to finish more often, which the next point
  cares about.
- `script_gen.py` enforces a hard word-count ceiling independent of the prompt, so a
  runaway generation can't turn into a much longer (much more expensive) render.
- `video_gen.py`'s retry logic no longer resubmits a whole new job if only the polling/
  download step hiccups after a successful submission — HeyGen bills on submission, so a
  naive retry-by-resubmitting would have silently double-charged for one video.
- Engine choice (`HEYGEN_ENGINE` in `.env`) matters a lot for cost — Avatar III is
  reportedly far cheaper per second than Avatar IV/V, but only works if your specific
  avatar was built to support it; worth checking in the HeyGen dashboard before switching.

**Shorts metadata is tuned to how discovery actually ranks in 2026**, not just keyword
density: title keyword in the first three words, a focused 8-12 tag list rather than a
maxed-out one, and 3-5 description hashtags with `#Shorts` first (YouTube renders the first
three description hashtags as clickable links above the title). The system prompt also
pushes hard against generic openings ("Hey guys, today...") in favor of a first-sentence
hook, since watch-through rate — not keywords — is what actually triggers wider algorithmic
distribution.

Sources: [HeyGen API pricing breakdown](https://www.g2.com/articles/heygen-api-pricing),
[HeyGen pricing explained](https://www.arcade.software/post/heygen-pricing),
[YouTube Shorts best practices 2026](https://joinbrands.com/blog/youtube-shorts-best-practices/),
[YouTube tags/hashtags SEO guide](https://hashtagtools.io/blog/youtube-hashtags-shorts-seo-guide-2026).

## Known limitations / possible next steps

- HeyGen's endpoint shapes in `video_gen.py` are based on their documented API surface at
  the time of writing — worth a quick diff against current docs if their API changes.
- Run history currently lives in a CSV committed back to the repo by the workflow; a real
  database or spreadsheet integration would scale better past a few hundred runs.
- No automated content moderation pass before publish — currently relies on the prompt
  constraints plus the public/unlisted staging period.
- Haven't yet tested `HEYGEN_ENGINE=avatar_iii` against the current avatar for a cheaper
  render — the account's Free-plan credits are limited, so this is worth trying carefully
  rather than by trial and error.
