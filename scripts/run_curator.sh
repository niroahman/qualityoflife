#!/bin/bash
set -euo pipefail

AGENT=${1:-"pro"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
AGENT_DIR="$REPO_DIR/agents/curator-$AGENT"
STATE_FILE="$REPO_DIR/.state/last-run-$AGENT.txt"
FEEDS_RAW=$(mktemp /tmp/feeds_raw_XXXXXX.md)

cleanup() {
  rm -f "$FEEDS_RAW" /tmp/runtime-prompt.md /tmp/runtime-feeds.yaml
}
trap cleanup EXIT

cd "$REPO_DIR"

echo "🚀 Starting curator-$AGENT..."

# 0. CONFIG
echo "⚙️  Fetching config from SilverBullet..."
.venv/bin/python "$SCRIPT_DIR/fetch_config.py" \
  --agent "$AGENT" \
  --template "$AGENT_DIR/system-prompt.template.md"

# 1. FETCH
echo "📡 Fetching feeds..."
.venv/bin/python "$SCRIPT_DIR/fetch_feeds.py" \
  --feeds /tmp/runtime-feeds.yaml \
  --output "$FEEDS_RAW" \
  --since-file "$STATE_FILE"

# 2. FILTER
echo "🤖 Filtering with AI..."
DIGEST_JSON=$(cat /tmp/runtime-prompt.md "$FEEDS_RAW" \
  | gemini "Read the system prompt and analyse the feeds below. Return JSON.")

# Validate JSON before publishing
if ! echo "$DIGEST_JSON" | .venv/bin/python -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
  echo "ERROR: Gemini did not return valid JSON" >&2
  echo "--- Gemini output ---" >&2
  echo "$DIGEST_JSON" >&2
  exit 1
fi

# 3. PUBLISH
echo "📤 Publishing to SilverBullet..."
echo "$DIGEST_JSON" | .venv/bin/python "$SCRIPT_DIR/publish_to_sb.py" --agent "$AGENT"

mkdir -p "$(dirname "$STATE_FILE")"
date -u +"%Y-%m-%dT%H:%M:%S" > "$STATE_FILE"
echo "✅ curator-$AGENT done!"
