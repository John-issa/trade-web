#!/usr/bin/env bash
set -euo pipefail

# Optional auto-update of friend repo before start
if [ -d "${REPO_DIR}" ] && [ -d "${REPO_DIR}/.git" ]; then
  git -C "${REPO_DIR}" fetch --all --prune || true
  git -C "${REPO_DIR}" checkout "${REPO_BRANCH:-main}" || true
  git -C "${REPO_DIR}" pull --rebase || true
fi

# Launch app server
exec gunicorn \
  -k uvicorn.workers.UvicornWorker \
  -w "${GUNICORN_WORKERS:-4}" \
  -b "0.0.0.0:${PORT:-8000}" \
  --timeout 120 \
  app.main:app