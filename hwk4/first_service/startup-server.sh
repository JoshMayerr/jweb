#!/bin/bash
# HW4 VM1 startup script. Edit PROJECT_ID and GIT_REPO_URL below for your setup.
set -e
export DEBIAN_FRONTEND=noninteractive

PROJECT_ID="cs528-jm"
GIT_REPO_URL="https://github.com/joshmayerr/jweb.git"

apt-get update -y
apt-get install -y python3 python3-venv git

export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export BUCKET="jweb-content"
export FORBIDDEN_TOPIC="jweb-forbidden"
export PORT="80"

git clone "$GIT_REPO_URL" /tmp/jweb || { echo "Clone failed."; exit 1; }
cd /tmp/jweb/hwk4/first_service
python3 -m venv /opt/jweb-venv
/opt/jweb-venv/bin/pip install -r requirements.txt
nohup /opt/jweb-venv/bin/python server.py </dev/null >>/var/log/jweb-server.log 2>&1 &
exit 0
