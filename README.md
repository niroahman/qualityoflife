# qualityoflife

Public repo for personal AI agents. Fork it, point it at your own SilverBullet.

**Principle: repo is the engine, SilverBullet is the fuel.**  
All personal data (profile, feeds, interests) lives in SilverBullet — not here. Scripts fetch config at runtime. Repo stays generic.

## Agents

| Agent | Purpose | Schedule |
|-------|---------|----------|
| `curator-pro` | Professional content curation (tech, architecture, leadership) | Monday 07:30 |
| `curator-personal` | Personal/hobby content curation | Friday 16:00 |

## Setup

1. Clone or fork this repo
2. Copy `.env.example` → `.env` and fill in your values
3. Create config pages in your SilverBullet (see below)
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `./scripts/run_curator.sh pro`

## SilverBullet config pages

Create these pages manually in SilverBullet before first run:

```
config/curator-pro/profile.md     ← your professional profile & interests
config/curator-pro/feeds.md       ← your RSS feeds (use agents/curator-pro/feeds.example.yaml as template)
config/curator-pro/sources.md     ← your YouTube channels, subreddits, GitHub repos
```

Same structure for `curator-personal`.

## Requirements

- Python 3.11+
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) with `GEMINI_API_KEY`
- SilverBullet instance with HTTP API access
