#!/bin/bash

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

LOCK_FILE=/var/log/hw9_monitor_startup_done
if [ -f "${LOCK_FILE}" ]; then
  echo "HW9 monitor startup already completed."
  exit 0
fi

PROJECT_ID="${PROJECT_ID:-cs528-jm}"
REPO_URL="${REPO_URL:-https://github.com/joshmayerr/jweb.git}"
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-jweb-forbidden-sub}"
BUCKET_NAME="${BUCKET_NAME:-jweb-content}"

apt-get update -y
apt-get install -y curl git

curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:${PATH}"

rm -rf /opt/jweb
git clone "${REPO_URL}" /opt/jweb

cd /opt/jweb/hw9
uv sync

cat >/etc/systemd/system/hw9-monitor.service <<EOF
[Unit]
Description=CS528 HW9 forbidden request monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/jweb/hw9
Environment=GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
Environment=FORBIDDEN_SUBSCRIPTION=${SUBSCRIPTION_ID}
Environment=BUCKET=${BUCKET_NAME}
ExecStart=/root/.local/bin/uv run monitor.py
Restart=always
RestartSec=2
StandardOutput=append:/var/log/hw9-monitor.log
StandardError=append:/var/log/hw9-monitor.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hw9-monitor.service
systemctl restart hw9-monitor.service

touch "${LOCK_FILE}"
