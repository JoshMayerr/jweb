#!/bin/bash

set -euo pipefail

export PROJECT_ID="${PROJECT_ID:-cs528-jm}"
export ZONE="${ZONE:-us-central1-c}"
export REGION="${REGION:-us-central1}"
export BUCKET_NAME="${BUCKET_NAME:-jweb-content}"
export SA_NAME="${SA_NAME:-jweb-hwk6-sa}"
export SA_EMAIL="${SA_EMAIL:-${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com}"
export VM_TRAIN_NAME="${VM_TRAIN_NAME:-jweb-hwk6-trainer}"
export DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-jweb-hwk5-mysql}"
export DB_NAME="${DB_NAME:-jwebhw5}"
export DB_USER="${DB_USER:-hw5user}"
export DB_PASSWORD="${DB_PASSWORD:-hw5password}"
export TRAIN_MACHINE_TYPE="${TRAIN_MACHINE_TYPE:-e2-small}"
export RESULTS_PREFIX="${RESULTS_PREFIX:-hwk6-results}"
export GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/joshmayerr/jweb.git}"
export RESULT_WAIT_SECONDS="${RESULT_WAIT_SECONDS:-1200}"
export RESULT_POLL_SECONDS="${RESULT_POLL_SECONDS:-20}"

echo "Using PROJECT_ID=${PROJECT_ID}, ZONE=${ZONE}, REGION=${REGION}"

gcloud config set project "${PROJECT_ID}"
gcloud config set compute/zone "${ZONE}"

gcloud services enable \
  compute.googleapis.com \
  storage.googleapis.com \
  logging.googleapis.com \
  sqladmin.googleapis.com

gcloud iam service-accounts create "${SA_NAME}" \
  --display-name="jweb HW6 service account" 2>/dev/null || true

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectUser"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client"

gcloud sql instances patch "${DB_INSTANCE_NAME}" \
  --activation-policy=ALWAYS \
  --quiet

export INSTANCE_CONNECTION_NAME
INSTANCE_CONNECTION_NAME="$(gcloud sql instances describe "${DB_INSTANCE_NAME}" --format='value(connectionName)')"

if gcloud compute instances describe "${VM_TRAIN_NAME}" --zone="${ZONE}" >/dev/null 2>&1; then
  gcloud compute instances delete "${VM_TRAIN_NAME}" --zone="${ZONE}" --quiet
fi

gcloud compute instances create "${VM_TRAIN_NAME}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type="${TRAIN_MACHINE_TYPE}" \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account="${SA_EMAIL}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --create-disk=auto-delete=yes,boot=yes,image-family=ubuntu-2404-lts-amd64,image-project=ubuntu-os-cloud,size=10,type=pd-balanced \
  --metadata=PROJECT_ID="${PROJECT_ID}",GIT_REPO_URL="${GIT_REPO_URL}",BUCKET_NAME="${BUCKET_NAME}",DB_NAME="${DB_NAME}",DB_USER="${DB_USER}",DB_PASSWORD="${DB_PASSWORD}",INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME}",RESULTS_PREFIX="${RESULTS_PREFIX}" \
  --metadata-from-file startup-script=hwk6/startup-trainer.sh

echo "Created VM ${VM_TRAIN_NAME}. Waiting for results in gs://${BUCKET_NAME}/${RESULTS_PREFIX}/"

deadline=$(( $(date +%s) + RESULT_WAIT_SECONDS ))
metrics_uri="gs://${BUCKET_NAME}/${RESULTS_PREFIX}/metrics.txt"
country_uri="gs://${BUCKET_NAME}/${RESULTS_PREFIX}/country_predictions.csv"
income_uri="gs://${BUCKET_NAME}/${RESULTS_PREFIX}/income_predictions.csv"

until gcloud storage ls "${metrics_uri}" >/dev/null 2>&1; do
  if [ "$(date +%s)" -ge "${deadline}" ]; then
    echo "Timed out waiting for ${metrics_uri}."
    echo "Inspect VM log with: gcloud compute ssh ${VM_TRAIN_NAME} --zone=${ZONE} --command='sudo tail -n 100 /var/log/jweb-hwk6-trainer.log'"
    exit 1
  fi
  sleep "${RESULT_POLL_SECONDS}"
done

temp_dir="$(mktemp -d)"
trap 'rm -rf "${temp_dir}"' EXIT

gcloud storage cp "${metrics_uri}" "${temp_dir}/metrics.txt"
gcloud storage cp "${country_uri}" "${temp_dir}/country_predictions.csv"
gcloud storage cp "${income_uri}" "${temp_dir}/income_predictions.csv"

echo
echo "metrics.txt"
cat "${temp_dir}/metrics.txt"
echo
echo "country_predictions.csv"
sed -n '1,10p' "${temp_dir}/country_predictions.csv"
echo
echo "income_predictions.csv"
sed -n '1,10p' "${temp_dir}/income_predictions.csv"
echo
echo "HW6 setup complete."
echo "Training VM: ${VM_TRAIN_NAME}"
echo "Cloud SQL instance: ${DB_INSTANCE_NAME}"
echo "Results prefix: gs://${BUCKET_NAME}/${RESULTS_PREFIX}/"
