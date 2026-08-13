#!/usr/bin/env bash
# Diff upstream home-assistant/core google_health component against our fork.
# Usage: sync_upstream.sh <ha-tag>   e.g. sync_upstream.sh 2026.9.0
set -euo pipefail

TAG="${1:?usage: sync_upstream.sh <ha-tag> (e.g. 2026.9.0)}"
REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

UPSTREAM_DIR="$TMP/google_health"
mkdir -p "$UPSTREAM_DIR"

# Resolve the tag to a commit SHA first so all files come from one tree.
SHA="$(gh api "repos/home-assistant/core/git/ref/tags/$TAG" --jq '.object.sha')"
TYPE="$(gh api "repos/home-assistant/core/git/ref/tags/$TAG" --jq '.object.type')"
if [ "$TYPE" = "tag" ]; then
  SHA="$(gh api "repos/home-assistant/core/git/tags/$SHA" --jq '.object.sha')"
fi
echo "upstream $TAG -> commit $SHA"

FILES="$(gh api "repos/home-assistant/core/contents/homeassistant/components/google_health?ref=$SHA" --jq '.[].name')"
for f in $FILES; do
  gh api -H "Accept: application/vnd.github.raw" \
    "repos/home-assistant/core/contents/homeassistant/components/google_health/$f?ref=$SHA" \
    > "$UPSTREAM_DIR/$f" || echo "WARN: failed to fetch $f"
done

DIFF=0
for f in "$UPSTREAM_DIR"/*; do
  name="$(basename "$f")"
  ours="$REPO_ROOT/custom_components/google_health_plus/$name"
  if [ ! -e "$ours" ]; then
    echo "NEW upstream file: $name"
    DIFF=1
  elif ! diff -u "$ours" "$f" > "$TMP/$name.diff"; then
    echo "--- $name changed upstream:"
    cat "$TMP/$name.diff"
    DIFF=1
  fi
done
for ours in "$REPO_ROOT"/custom_components/google_health_plus/*; do
  name="$(basename "$ours")"
  [ -e "$UPSTREAM_DIR/$name" ] || { echo "REMOVED upstream (we keep): $name"; }
done

if [ "$DIFF" -eq 0 ]; then
  echo "No upstream changes since our snapshot."
else
  echo ""
  echo "Upstream SHA for UPSTREAM.md after porting: $SHA"
fi
