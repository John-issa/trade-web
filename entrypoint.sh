#!/usr/bin/env bash
set -euo pipefail

# 1) Ensure trade-repo exists, then update it
if [ ! -d "$REPO_DIR/.git" ]; then
  echo "[entrypoint] Cloning $REPO_GIT into $REPO_DIR"
  rm -rf "$REPO_DIR"
  git clone --depth 1 "$REPO_GIT" "$REPO_DIR"
else
  echo "[entrypoint] Pulling latest in $REPO_DIR"
  git -C "$REPO_DIR" pull --ff-only || true
fi

# 2) Install trade-repo deps if present
if [ -f "$REPO_DIR/requirements.txt" ]; then
  echo "[entrypoint] Installing trade-repo requirements"
  pip install --no-cache-dir -r "$REPO_DIR/requirements.txt"
else
  echo "[entrypoint] No trade-repo/requirements.txt found (skipping)"
fi

# 3) Run the app
echo "[entrypoint] Starting app: $*"
exec "$@"
