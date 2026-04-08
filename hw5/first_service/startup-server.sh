#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

LOCK_FILE=/var/log/hwk5_web_startup_done

if [ -f "${LOCK_FILE}" ]; then
  echo "Startup script already ran once. Skipping."
  exit 0
fi

PROJECT_ID="cs528-jm"
GIT_REPO_URL="https://github.com/joshmayerr/jweb.git"
BUCKET_NAME="jweb-content"
FORBIDDEN_TOPIC_VALUE="jweb-forbidden"
PORT_VALUE="80"
DB_NAME_VALUE="jwebhw5"
DB_USER_VALUE="hw5user"
DB_PASSWORD_VALUE="hw5password"
INSTANCE_CONNECTION_NAME_VALUE="cs528-jm:us-central1:jweb-hwk5-mysql"

apt-get update -y
apt-get install -y git python3 python3-venv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:${PATH}"

git clone "${GIT_REPO_URL}" /opt/jweb
cd /opt/jweb

export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export BUCKET="${BUCKET_NAME}"
export FORBIDDEN_TOPIC="${FORBIDDEN_TOPIC_VALUE}"
export PORT="${PORT_VALUE}"
export DB_NAME="${DB_NAME_VALUE}"
export DB_USER="${DB_USER_VALUE}"
export DB_PASSWORD="${DB_PASSWORD_VALUE}"
export INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME_VALUE}"
export TIMING_LOG_INTERVAL="1000"

uv sync --project hwk5/first_service
nohup uv run --project hwk5/first_service hwk5/first_service/main.py \
  </dev/null >/var/log/jweb-hwk5-server.log 2>&1 &

touch "${LOCK_FILE}"
