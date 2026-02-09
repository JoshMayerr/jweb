#!/usr/bin/env bash
set -e

BUCKET="${BUCKET:-jweb-content}"
DATA_DIR="${DATA_DIR:-./web}"

if [ "$1" = "download" ]; then
  mkdir -p "$DATA_DIR"
  gsutil -m cp -r "gs://${BUCKET}/web/*" "$DATA_DIR/" 2>/dev/null || \
  gcloud storage cp -r "gs://${BUCKET}/web/*" "$DATA_DIR/" || \
  (echo "Error: need gsutil or gcloud" && exit 1)
elif [ "$1" = "run" ]; then
  python hw2.py --data-dir "$DATA_DIR"
else
  mkdir -p "$DATA_DIR"
  gsutil -m cp -r "gs://${BUCKET}/web/*" "$DATA_DIR/" 2>/dev/null || \
  gcloud storage cp -r "gs://${BUCKET}/web/*" "$DATA_DIR/" || \
  (echo "Error: need gsutil or gcloud" && exit 1)
  python hw2.py --data-dir "$DATA_DIR"
fi
