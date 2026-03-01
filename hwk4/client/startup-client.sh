#!/bin/bash
# Optional VM2 startup script: clone repo so client is available after SSH.
# Then: cd /tmp/jweb/hwk4/client && python3 run_client.py http://<WEB_STATIC_IP>:8080 -n 100
set -e
export DEBIAN_FRONTEND=noninteractive

GIT_REPO_URL="https://github.com/joshmayerr/jweb.git"

apt-get update -y
apt-get install -y python3 git

git clone "$GIT_REPO_URL" /tmp/jweb || true
exit 0
