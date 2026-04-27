#!/bin/bash

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-cs528-jm}"
REGION="${REGION:-us-central1}"
ZONE="${ZONE:-us-central1-b}"
CLUSTER_NAME="${CLUSTER_NAME:-hw9-cluster}"
TOPIC_NAME="${TOPIC_NAME:-jweb-forbidden}"
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-jweb-forbidden-sub}"
SA_WEB_NAME="${SA_WEB_NAME:-jweb-hw9-sa}"
SA_WEB_EMAIL="${SA_WEB_EMAIL:-${SA_WEB_NAME}@${PROJECT_ID}.iam.gserviceaccount.com}"
MONITOR_VM_NAME="${MONITOR_VM_NAME:-hw9-monitor}"
AR_REPO="${AR_REPO:-hw9}"
BUCKET_NAME="${BUCKET_NAME:-jweb-content}"

echo "Cleaning up HW9 resources in project ${PROJECT_ID}"

gcloud config set project "${PROJECT_ID}"
gcloud config set compute/zone "${ZONE}"

if gcloud container clusters describe "${CLUSTER_NAME}" --region="${REGION}" >/dev/null 2>&1; then
  gcloud container clusters get-credentials "${CLUSTER_NAME}" --region="${REGION}" >/dev/null 2>&1 || true
  kubectl delete service hw9-web --ignore-not-found=true || true
  kubectl delete deployment hw9-web --ignore-not-found=true || true
fi

gcloud compute instances delete "${MONITOR_VM_NAME}" --zone="${ZONE}" --quiet || true
gcloud container clusters delete "${CLUSTER_NAME}" --region="${REGION}" --quiet || true

gcloud pubsub subscriptions delete "${SUBSCRIPTION_ID}" --quiet || true
gcloud pubsub topics delete "${TOPIC_NAME}" --quiet || true

gcloud artifacts repositories delete "${AR_REPO}" --location="${REGION}" --quiet || true

gcloud storage buckets remove-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/storage.objectViewer" \
  --quiet || true

gcloud storage buckets remove-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/storage.objectUser" \
  --quiet || true

gcloud pubsub topics remove-iam-policy-binding "${TOPIC_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/pubsub.publisher" \
  --quiet || true

gcloud pubsub subscriptions remove-iam-policy-binding "${SUBSCRIPTION_ID}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/pubsub.subscriber" \
  --quiet || true

gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/logging.logWriter" \
  --quiet || true

gcloud iam service-accounts delete "${SA_WEB_EMAIL}" --quiet || true

echo "HW9 cleanup complete."
