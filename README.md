# qualityoflife

<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/13a319eb-e7ec-420c-a26c-26c7f9853af7" />


Public repo for personal AI agents. Fork it, point it at your own SilverBullet.

**Principle: repo is the engine, SilverBullet is the fuel.**  
All personal data (profile, feeds, interests) lives in SilverBullet — not here. Scripts fetch config at runtime. Repo stays generic.

## Agents

| Agent | Purpose | Schedule |
|-------|---------|----------|
| `curator-pro` | Professional content curation (tech, architecture, leadership) | Monday 07:30 |
| `curator-personal` | Personal/hobby content curation | Friday 16:00 |

## Implementations

This repo contains two implementations of the same idea, side by side:

- **Code-first** (`agents/`, `scripts/`) — the original Python and Shell pipeline, runs both curators on the schedules above, publishes to SilverBullet.
- **Workflow-first** (`n8n/`) — an n8n workflow that does the tech-newsletter slice and delivers a top-5 digest to Telegram instead of a wiki page. Built as a hands-on evaluation of where visual workflow tools belong in an AI-native dev stack. See [`n8n/README.md`](n8n/README.md) for setup and the comparison.

## Setup

1. Clone or fork this repo
2. Copy `.env.example` → `~/.secrets/qualityoflife/.env` and fill in your values (`chmod 600` it)
3. Create config pages in your SilverBullet (see below)
4. Create venv and install dependencies: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`
5. Run: `./scripts/run_curator.sh pro`

## SilverBullet config pages

Create these pages manually in SilverBullet before first run:

```
config/curator-pro/profile.md     ← your professional profile & interests
config/curator-pro/feeds.md       ← all feeds: RSS, podcasts, YouTube channels, subreddits, GitHub repos
                                     (use agents/curator-pro/feeds.example.yaml as template)
```

Same structure for `curator-personal`.

## Requirements

- Python 3.11+
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) with `GEMINI_API_KEY`
- SilverBullet instance with HTTP API access
