#!/bin/bash

# =============================================================================
# HW4 cleanup.sh
# =============================================================================
# This script tears down ALL infrastructure created by hw4/setup.sh.
# It is intended to be run from the repo root as:
#   pushd hw4
#   bash cleanup.sh
#   popd
# =============================================================================

set -euo pipefail

# ---------- Variables (must match setup.sh) ----------
export PROJECT_ID="${PROJECT_ID:-cs528-jm}"
export ZONE="${ZONE:-us-central1-c}"
export REGION="${REGION:-us-central1}"
export BUCKET_NAME="${BUCKET_NAME:-jweb-content}"
export FORBIDDEN_TOPIC="${FORBIDDEN_TOPIC:-jweb-forbidden}"
export FORBIDDEN_SUB="${FORBIDDEN_SUB:-jweb-forbidden-sub}"
export SA_WEB_NAME="${SA_WEB_NAME:-jweb-file-server-sa}"
export SA_WEB_EMAIL="${SA_WEB_EMAIL:-${SA_WEB_NAME}@${PROJECT_ID}.iam.gserviceaccount.com}"
export VM_WEB_NAME="${VM_WEB_NAME:-jweb-web-server}"
export VM_CLIENT_NAME="${VM_CLIENT_NAME:-jweb-client}"
export VM_SUB_NAME="${VM_SUB_NAME:-jweb-forbidden-subscriber}"
export STATIC_IP_NAME="${STATIC_IP_NAME:-jweb-web-ip}"

echo "Cleaning up HW4 resources in PROJECT_ID=${PROJECT_ID}, ZONE=${ZONE}, REGION=${REGION}"

# Ensure project/zone are set (mirrors setup.sh)
gcloud config set project "${PROJECT_ID}"
gcloud config set compute/zone "${ZONE}"

# ---------- 1. Delete VM instances ----------
gcloud compute instances delete "${VM_WEB_NAME}" "${VM_CLIENT_NAME}" "${VM_SUB_NAME}" \
  --zone="${ZONE}" --quiet || true

# ---------- 2. Release static IP address ----------
gcloud compute addresses delete "${STATIC_IP_NAME}" \
  --region="${REGION}" --quiet || true

# ---------- 3. Delete firewall rule ----------
gcloud compute firewall-rules delete allow-jweb-http --quiet || true

# ---------- 4. Delete Pub/Sub subscription and topic ----------
gcloud pubsub subscriptions delete "${FORBIDDEN_SUB}" --quiet || true
gcloud pubsub topics delete "${FORBIDDEN_TOPIC}" --quiet || true

# ---------- 5. Remove IAM bindings for the service account ----------

# Bucket bindings
gcloud storage buckets remove-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/storage.objectViewer" --quiet || true

gcloud storage buckets remove-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/storage.objectUser" --quiet || true

# Pub/Sub topic binding
gcloud pubsub topics remove-iam-policy-binding "${FORBIDDEN_TOPIC}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/pubsub.publisher" --quiet || true

# Pub/Sub subscription binding
gcloud pubsub subscriptions remove-iam-policy-binding "${FORBIDDEN_SUB}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/pubsub.subscriber" --quiet || true

# Project-level logging binding
gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/logging.logWriter" --quiet || true

# ---------- 6. Delete the service account ----------
gcloud iam service-accounts delete "${SA_WEB_EMAIL}" --quiet || true

# ---------- 7. Optional: revoke application default credentials ----------
# Only needed if you used `gcloud auth application-default login` for HW4.
# gcloud auth application-default revoke || true

echo "HW4 cleanup complete."

