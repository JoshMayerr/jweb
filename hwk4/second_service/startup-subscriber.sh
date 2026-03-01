#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

PROJECT_ID="cs528-jm"
GIT_REPO_URL="https://github.com/joshmayerr/jweb.git"

apt-get update -y
apt-get install -y python3 python3-pip git

export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export BUCKET="jweb-content"
export FORBIDDEN_SUBSCRIPTION="jweb-forbidden-sub"

git clone "$GIT_REPO_URL" /tmp/jweb || { echo "Clone failed."; exit 1; }
cd /tmp/jweb/hwk4/second_service
pip3 install -r requirements.txt
nohup python3 main.py </dev/null >>/var/log/jweb-subscriber.log 2>&1 &
exit 0
