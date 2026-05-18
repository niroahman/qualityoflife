# Agent Instructions — qualityoflife

This repo runs AI-curated weekly digests fetched from RSS/Atom/YouTube feeds,
filtered by Gemini, and published to SilverBullet.

## Environment setup

Secrets live in `~/.secrets/qualityoflife/.env`. Must be loaded before running scripts.

Python scripts (`scripts/auth.py`) load it automatically via `python-dotenv` — no manual step needed when using the venv.

For shell-level commands or ad-hoc runs:

```bash
# Activate venv + load env
source .venv/bin/activate
set -a; source ~/.secrets/qualityoflife/.env; set +a
```

Ad-hoc Python (no shell sourcing needed — dotenv handles it):

```bash
.venv/bin/python scripts/some_script.py
```

Required vars listed in `.env.example`.

## Pipeline overview

```
fetch_config.py  →  fetch_feeds.py  →  gemini filter  →  publish_to_sb.py
```

Run: `./scripts/run_curator.sh pro` or `./scripts/run_curator.sh personal`

State file: `.state/last-run-{agent}.txt` — updated on success, controls fetch window.

## Agents

| Agent      | Command                              | Digest page           | Topics                                      |
|------------|--------------------------------------|-----------------------|---------------------------------------------|
| `pro`      | `./scripts/run_curator.sh pro`       | `Digest/YYYY-Www-pro` | Tech, Go, Python, AI, architecture          |
| `personal` | `./scripts/run_curator.sh personal`  | `Digest/YYYY-Www-personal` | Homelab, emulointi, e-readers, pelit, TV, kirjat |

## SilverBullet config (personal, not in repo)

All user config lives in SilverBullet under `config/curator-{agent}/`:

| File           | Contents                                              |
|----------------|-------------------------------------------------------|
| `profile.md`   | User profile injected as `{{PROFILE}}`                |
| `feeds.md`     | YAML: newsletters, podcasts, tech_blogs, youtube_channels, reddit_forums, github_releases |
| `import.md`    | **Pending imports** — see below                       |

Personal digest output is grouped by category:
🏠 Homelab · 🕹️ Emulointi & Retro · 📖 Lukulaitteet · 🎮 Pelit · 📺 TV & Elokuvat · 📚 Kirjat

## Import workflow

`config/curator-{agent}/import.md` in SilverBullet is a queue for
new feeds/channels. Each line is a free-text hint,
e.g. "melkeyn youtube kanava" or "add syntax podcast".

**At the start of every session, check both agents' import files:**

```python
# Quick check:
from scripts.auth import SB_BASE_URL, get_session
s = get_session()
for agent in ("pro", "personal"):
    r = s.get(f"{SB_BASE_URL}/.fs/config/curator-{agent}/import.md", timeout=15)
    r.encoding = "utf-8"
    if r.status_code == 200 and r.text.strip():
        print(f"=== import.md ({agent}) ===")
        print(r.text)
```

For each non-empty line:
1. Interpret what feed/channel it refers to
2. Check if already in `config/curator-{agent}/feeds.md`
3. If missing: find the feed URL (YouTube channel ID, RSS URL), verify it works,
   add it to both SilverBullet feeds.md and `agents/curator-{agent}/feeds.example.yaml`
4. Remove the processed line (or clear the file if all done)

## YouTube channels

YouTube feeds use channel IDs, not @handles:
`https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxx`

To resolve a @handle to a channel ID, use the web search agent — YouTube
blocks direct scraping with consent redirects.

## Feed sections

`feeds.md` supports these sections (type inferred from section name):

- `newsletters` → type: newsletter
- `podcasts` → type: podcast (renders episode page + MP3 links)
- `tech_blogs` → type: blog
- `youtube_channels` → type: youtube (renders ▶ video link)

## System prompt templates

`agents/curator-{agent}/system-prompt.template.md`

- Pro: `{{PROFILE}}` replaced at runtime. JSON fields: `otsikko`, `linkki`, `lahde`, `lahde_tyyppi`, `pisteet`, `perustelu`, `podcast_sivu`, `podcast_mp3`.
- Personal: same + `{{FAVORITES}}` replaced from `favorites.md` (optional). Extra JSON field: `kategoria` (homelab | emulointi | lukulaite | pelit | tv_elokuva | kirjat).

## Feeds examples

`agents/curator-{agent}/feeds.example.yaml` — kept in sync with SilverBullet.
When adding feeds, update both the SilverBullet page and the example file.
