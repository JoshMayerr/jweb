#!/bin/bash

set -euo pipefail

export PROJECT_ID="${PROJECT_ID:-cs528-jm}"
export ZONE="${ZONE:-us-central1-c}"
export REGION="${REGION:-us-central1}"
export VM_WEB_NAME="${VM_WEB_NAME:-jweb-hwk5-web}"
export VM_SUB_NAME="${VM_SUB_NAME:-jweb-hwk5-subscriber}"
export DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-jweb-hwk5-mysql}"

echo "Stopping HW5 resources in PROJECT_ID=${PROJECT_ID}, ZONE=${ZONE}, REGION=${REGION}"

gcloud config set project "${PROJECT_ID}"
gcloud config set compute/zone "${ZONE}"

gcloud compute instances stop "${VM_WEB_NAME}" --zone="${ZONE}" --quiet || true
gcloud compute instances stop "${VM_SUB_NAME}" --zone="${ZONE}" --quiet || true
gcloud sql instances patch "${DB_INSTANCE_NAME}" --activation-policy=NEVER --quiet || true

echo "HW5 resources stopped."
