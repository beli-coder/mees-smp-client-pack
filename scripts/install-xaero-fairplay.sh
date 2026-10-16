#!/usr/bin/env bash
set -euo pipefail

# SERVER ONLY. Does not require a client mod. Uses the well-known Modrinth
# datapack release 1.1.0. Install while minecraft is running, then /reload.
VERSION_ID=93bxF9lv
GAME_VERSION=26.3
DEST_DIR=/opt/minecraft/server/world/datapacks
DEST_FILE="$DEST_DIR/xaeros-map-server-utils-1.1.0.zip"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

curl -fsSL --retry 3 \
  "https://api.modrinth.com/v2/version/$VERSION_ID" >"$TMP/version.json"
jq -e --arg game "$GAME_VERSION" '
  (.game_versions | index($game)) != null and
  (.loaders | index("datapack")) != null
' "$TMP/version.json" >/dev/null
jq -er '.files | (map(select(.primary == true and (.filename | endswith(".zip")))) | .[0]) // (map(select(.filename | endswith(".zip"))) | .[0])' \
  "$TMP/version.json" >"$TMP/file.json"
URL=$(jq -er '.url' "$TMP/file.json")
HASH=$(jq -er '.hashes.sha512' "$TMP/file.json")
curl -fsSL --retry 3 "$URL" >"$TMP/pack.zip"
printf '%s  %s\n' "$HASH" "$TMP/pack.zip" | sha512sum -c -
unzip -tq "$TMP/pack.zip"
unzip -Z1 "$TMP/pack.zip" | grep -Eq '^pack\.mcmeta$' || {
  echo 'ERROR: pack.mcmeta missing from archive root. Aborting.' >&2
  exit 1
}
sudo install -d -o minecraft -g minecraft -m 0750 "$DEST_DIR"
if sudo test -e "$DEST_FILE"; then
  echo "Already installed: $DEST_FILE" >&2
  exit 1
fi
sudo install -o minecraft -g minecraft -m 0640 "$TMP/pack.zip" "$DEST_FILE"
echo "Installed: $DEST_FILE"
echo "Now in Minecraft, run /reload, then /function xaero:autorun/set/fairxaero"
echo "Rejoin with Xaero client to verify cave map and radar are restricted."
