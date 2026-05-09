#!/bin/bash
set -euo pipefail

AGENT=${1:-"pro"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
AGENT_DIR="$REPO_DIR/agents/curator-$AGENT"
FEEDS_RAW=$(mktemp /tmp/feeds_raw_XXXXXX.md)

cleanup() {
  rm -f "$FEEDS_RAW" /tmp/runtime-prompt.md /tmp/runtime-feeds.yaml /tmp/runtime-sources.yaml
}
trap cleanup EXIT

cd "$REPO_DIR"

echo "🚀 Käynnistetään curator-$AGENT..."

# 0. CONFIG
echo "⚙️  Haetaan konfiguraatio SilverBulletista..."
.venv/bin/python "$SCRIPT_DIR/fetch_config.py" \
  --agent "$AGENT" \
  --template "$AGENT_DIR/system-prompt.template.md"

# 1. FETCH
echo "📡 Haetaan syötteet..."
.venv/bin/python "$SCRIPT_DIR/fetch_feeds.py" \
  --feeds /tmp/runtime-feeds.yaml \
  --output "$FEEDS_RAW"

# 2. FILTER
echo "🤖 Filtteröidään AI:lla..."
DIGEST_JSON=$(cat /tmp/runtime-prompt.md "$FEEDS_RAW" \
  | gemini "Lue system prompt ja analysoi alla olevat syötteet. Palauta JSON.")

# 3. PUBLISH
echo "📤 Julkaistaan SilverBulletiin..."
echo "$DIGEST_JSON" | .venv/bin/python "$SCRIPT_DIR/publish_to_sb.py" --agent "$AGENT"

echo "✅ curator-$AGENT valmis!"
