#!/bin/bash

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-cs528-jm}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-b}"
CLUSTER_NAME="${CLUSTER_NAME:-hw9-cluster}"
BUCKET_NAME="${BUCKET_NAME:-jweb-content}"
TOPIC_NAME="${TOPIC_NAME:-jweb-forbidden}"
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-jweb-forbidden-sub}"
SA_WEB_NAME="${SA_WEB_NAME:-jweb-hw9-sa}"
SA_WEB_EMAIL="${SA_WEB_EMAIL:-${SA_WEB_NAME}@${PROJECT_ID}.iam.gserviceaccount.com}"
MONITOR_VM_NAME="${MONITOR_VM_NAME:-hw9-monitor}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-micro}"
REPO_URL="${REPO_URL:-https://github.com/joshmayerr/jweb.git}"
AR_REPO="${AR_REPO:-hw9}"
IMAGE_NAME="${IMAGE_NAME:-hw9-web}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${IMAGE_NAME}:latest"

gcloud config set project "${PROJECT_ID}"
gcloud config set compute/zone "${ZONE}"

gcloud services enable \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  container.googleapis.com \
  iam.googleapis.com \
  logging.googleapis.com \
  pubsub.googleapis.com \
  storage.googleapis.com

gcloud iam service-accounts create "${SA_WEB_NAME}" \
  --display-name="jweb HW9 web and monitor service account" \
  2>/dev/null || true

sleep 10

gcloud artifacts repositories create "${AR_REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  2>/dev/null || true

gcloud pubsub topics create "${TOPIC_NAME}" 2>/dev/null || true
gcloud pubsub subscriptions create "${SUBSCRIPTION_ID}" --topic="${TOPIC_NAME}" 2>/dev/null || true

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/storage.objectViewer"

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/storage.objectUser"

gcloud pubsub topics add-iam-policy-binding "${TOPIC_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/pubsub.publisher"

gcloud pubsub subscriptions add-iam-policy-binding "${SUBSCRIPTION_ID}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/logging.logWriter"

gcloud container clusters create-auto "${CLUSTER_NAME}" \
  --region="${REGION}" \
  --service-account="${SA_WEB_EMAIL}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  2>/dev/null || true

gcloud container clusters get-credentials "${CLUSTER_NAME}" --region="${REGION}"

gcloud builds submit . --tag "${IMAGE_URI}" --project="${PROJECT_ID}" --gcs-log-dir="gs://${BUCKET_NAME}/build-logs"

sed \
  -e "s|REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/hw9-web:latest|${IMAGE_URI}|g" \
  -e "s|value: jweb-content|value: ${BUCKET_NAME}|g" \
  -e "s|value: PROJECT_ID|value: ${PROJECT_ID}|g" \
  deployment.yaml | kubectl apply -f -

kubectl apply -f service.yaml

VM_ARGS=(
  --zone="${ZONE}"
  --machine-type="${MACHINE_TYPE}"
  --image-family=ubuntu-2204-lts
  --image-project=ubuntu-os-cloud
  --service-account="${SA_WEB_EMAIL}"
  --scopes=https://www.googleapis.com/auth/cloud-platform
  --metadata=PROJECT_ID="${PROJECT_ID}",REPO_URL="${REPO_URL}",SUBSCRIPTION_ID="${SUBSCRIPTION_ID}",BUCKET_NAME="${BUCKET_NAME}"
  --metadata-from-file startup-script=startup-monitor.sh
)

gcloud compute instances create "${MONITOR_VM_NAME}" "${VM_ARGS[@]}" 2>/dev/null || true

kubectl get service hw9-web
echo "Image pushed to ${IMAGE_URI}"
echo "HW9 setup complete."
echo "Using shared service account ${SA_WEB_EMAIL} for the GKE web app and monitor VM."
