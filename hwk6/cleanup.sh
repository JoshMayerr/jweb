#!/bin/bash

set -euo pipefail

export PROJECT_ID="${PROJECT_ID:-cs528-jm}"
export ZONE="${ZONE:-us-central1-c}"
export REGION="${REGION:-us-central1}"
export VM_TRAIN_NAME="${VM_TRAIN_NAME:-jweb-hwk6-trainer}"
export DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-jweb-hwk5-mysql}"

echo "Stopping HW6 resources in PROJECT_ID=${PROJECT_ID}, ZONE=${ZONE}, REGION=${REGION}"

gcloud config set project "${PROJECT_ID}"
gcloud config set compute/zone "${ZONE}"

gcloud compute instances stop "${VM_TRAIN_NAME}" --zone="${ZONE}" --quiet || true
gcloud sql instances patch "${DB_INSTANCE_NAME}" --activation-policy=NEVER --quiet || true

echo "HW6 resources stopped."
