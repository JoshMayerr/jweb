#!/usr/bin/env bash
set -e

BUCKET="${BUCKET:-jweb-content}"
DATA_DIR="${DATA_DIR:-./web}"

if [ "$1" = "download" ]; then
  mkdir -p "$DATA_DIR"
  gsutil -m cp -r "gs://${BUCKET}/web/*" "$DATA_DIR/"
elif [ "$1" = "run" ]; then
  python -u hw2.py --data-dir "$DATA_DIR"
else
  mkdir -p "$DATA_DIR"
  gsutil -m cp -r "gs://${BUCKET}/web/*" "$DATA_DIR/"
  python -u hw2.py --data-dir "$DATA_DIR"
fi
