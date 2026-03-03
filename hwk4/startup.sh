#!/bin/bash

# =============================================================================
# HW4 root startup.sh for VM1 (web server)
# =============================================================================
# This script is passed to the VM via:
#   --metadata-from-file startup-script=hw4/startup.sh
# and is responsible for configuring the web server VM internally.
# It uses a lock file so it only runs once per VM boot disk.
# =============================================================================

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

LOCK_FILE=/var/log/startup_already_done

if [ -f "${LOCK_FILE}" ]; then
  echo "Startup script already ran once. Skipping."
  exit 0
fi

PROJECT_ID="cs528-jm"
GIT_REPO_URL="https://github.com/joshmayerr/jweb.git"

export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export BUCKET="jweb-content"
export FORBIDDEN_TOPIC="jweb-forbidden"
export PORT="80"

echo "Running HW4 web server startup on VM1..."

apt-get update -y
apt-get install -y python3 python3-venv git

git clone "${GIT_REPO_URL}" /tmp/jweb || { echo "Clone failed."; exit 1; }
cd /tmp/jweb/hwk4/first_service

python3 -m venv /opt/jweb-venv
/opt/jweb-venv/bin/pip install -r requirements.txt

nohup /opt/jweb-venv/bin/python server.py </dev/null >>/var/log/jweb-server.log 2>&1 &

touch "${LOCK_FILE}"

echo "HW4 web server startup completed."

exit 0

