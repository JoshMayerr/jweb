#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

LOCK_FILE=/var/log/hwk5_subscriber_startup_done

if [ -f "${LOCK_FILE}" ]; then
  echo "Startup script already ran once. Skipping."
  exit 0
fi

PROJECT_ID="cs528-jm"
GIT_REPO_URL="https://github.com/joshmayerr/jweb.git"
BUCKET_NAME="jweb-content"
FORBIDDEN_SUBSCRIPTION="jweb-forbidden-sub"

apt-get update -y
apt-get install -y git python3 python3-venv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:${PATH}"

git clone "${GIT_REPO_URL}" /opt/jweb
cd /opt/jweb

export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export BUCKET="${BUCKET_NAME}"
export FORBIDDEN_SUBSCRIPTION="${FORBIDDEN_SUBSCRIPTION}"

uv sync --project hwk5/second_service
nohup uv run --project hwk5/second_service hwk5/second_service/main.py \
  </dev/null >/var/log/jweb-hwk5-subscriber.log 2>&1 &

touch "${LOCK_FILE}"
