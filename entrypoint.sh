#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="${REPO_DIR:-/srv/trade-repo}"
REPO_GIT="${REPO_GIT:-https://github.com/slsecret/options-trading-assistant}"

echo "[entrypoint] REPO_DIR=$REPO_DIR  REPO_GIT=$REPO_GIT"
mkdir -p "$REPO_DIR"

if [ -d "$REPO_DIR/.git" ]; then
  echo "[entrypoint] Pull latest"
  git -C "$REPO_DIR" fetch --depth 1 origin || true
  DEFAULT_REF="$(git -C "$REPO_DIR" symbolic-ref --quiet --short refs/remotes/origin/HEAD | sed 's|origin/||' || echo main)"
  git -C "$REPO_DIR" reset --hard "origin/${DEFAULT_REF}" || true
else
  if [ -z "$(ls -A "$REPO_DIR" 2>/dev/null)" ]; then
    echo "[entrypoint] Clone into empty dir"
    git clone --depth 1 "$REPO_GIT" "$REPO_DIR"
  else
    echo "[entrypoint] Non-git dir; bootstrap via temp clone"
    TMP="$(mktemp -d)"; git clone --depth 1 "$REPO_GIT" "$TMP"
    rsync -a --delete --exclude='.git' "$TMP"/ "$REPO_DIR"/
    rm -rf "$TMP"
  fi
fi

if [ -f "$REPO_DIR/requirements.txt" ]; then
  echo "[entrypoint] Install trade-repo requirements"
  pip install --no-cache-dir -r "$REPO_DIR/requirements.txt"
fi

echo "[entrypoint] Starting: $*"
exec "$@"
