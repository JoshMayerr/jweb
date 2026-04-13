#!/bin/bash

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

LOCK_FILE=/var/log/hw8_startup_done
if [ -f "${LOCK_FILE}" ]; then
  echo "HW8 startup already completed."
  exit 0
fi

PROJECT_ID="${PROJECT_ID:-cs528-jm}"
REPO_URL="${REPO_URL:-https://github.com/joshmayerr/jweb.git}"
BUCKET_NAME="${BUCKET_NAME:-jweb-content}"
PORT="${PORT:-80}"

apt-get update -y
apt-get install -y curl git

curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:${PATH}"

rm -rf /opt/jweb
git clone "${REPO_URL}" /opt/jweb

cd /opt/jweb/hw8
uv sync

cat >/etc/systemd/system/hw8-server.service <<EOF
[Unit]
Description=CS528 HW8 file server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/jweb/hw8
Environment=GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
Environment=BUCKET=${BUCKET_NAME}
Environment=PORT=${PORT}
ExecStart=/root/.local/bin/uv run server.py
Restart=always
RestartSec=2
StandardOutput=append:/var/log/hw8-server.log
StandardError=append:/var/log/hw8-server.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hw8-server.service
systemctl restart hw8-server.service

touch "${LOCK_FILE}"
