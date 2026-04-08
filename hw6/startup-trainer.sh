#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

LOCK_FILE=/var/log/hwk6_trainer_startup_done
LOG_FILE=/var/log/jweb-hwk6-trainer.log

if [ -f "${LOCK_FILE}" ]; then
  echo "Startup script already ran once. Skipping."
  exit 0
fi

get_metadata() {
  curl -fsH "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"
}

PROJECT_ID="$(get_metadata PROJECT_ID)"
GIT_REPO_URL="$(get_metadata GIT_REPO_URL)"
BUCKET_NAME="$(get_metadata BUCKET_NAME)"
DB_NAME_VALUE="$(get_metadata DB_NAME)"
DB_USER_VALUE="$(get_metadata DB_USER)"
DB_PASSWORD_VALUE="$(get_metadata DB_PASSWORD)"
INSTANCE_CONNECTION_NAME_VALUE="$(get_metadata INSTANCE_CONNECTION_NAME)"
RESULTS_PREFIX_VALUE="$(get_metadata RESULTS_PREFIX)"

apt-get update -y
apt-get install -y curl git python3 python3-venv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:${PATH}"

git clone "${GIT_REPO_URL}" /opt/jweb
cd /opt/jweb

export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export BUCKET="${BUCKET_NAME}"
export DB_NAME="${DB_NAME_VALUE}"
export DB_USER="${DB_USER_VALUE}"
export DB_PASSWORD="${DB_PASSWORD_VALUE}"
export INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME_VALUE}"
export RESULTS_PREFIX="${RESULTS_PREFIX_VALUE}"
export PYTHONUNBUFFERED=1

uv sync --project hwk6
nohup uv run --project hwk6 hwk6/train_models.py \
  </dev/null >"${LOG_FILE}" 2>&1 &

touch "${LOCK_FILE}"
