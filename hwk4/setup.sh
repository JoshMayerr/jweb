#!/bin/bash

# =============================================================================
# HW4 setup.sh
# =============================================================================
# This script provisions ALL infrastructure required for HW4.
# It is intended to be run from the repo root as:
#   pushd hw4
#   bash setup.sh
#   popd
# =============================================================================

set -euo pipefail

# ---------- Variables (edit for your project) ----------
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

echo "Using PROJECT_ID=${PROJECT_ID}, ZONE=${ZONE}, REGION=${REGION}"

# ---------- 1. Set project and zone ----------
gcloud config set project "${PROJECT_ID}"
gcloud config set compute/zone "${ZONE}"

# ---------- 2. Enable APIs ----------
gcloud services enable compute.googleapis.com storage.googleapis.com pubsub.googleapis.com logging.googleapis.com

# ---------- 3. Firewall: allow ports 80 and 8080 to VMs with tag http-server ----------
gcloud compute firewall-rules create allow-jweb-http \
  --project="${PROJECT_ID}" \
  --network=default \
  --allow tcp:80,tcp:8080 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server \
  --description "HW4 web server" 2>/dev/null || true

# ---------- 4. Create service account ----------
gcloud iam service-accounts create "${SA_WEB_NAME}" \
  --display-name="jweb HW4 file server VM" 2>/dev/null || true

# ---------- 5. Create Pub/Sub topic and subscription ----------
gcloud pubsub topics create "${FORBIDDEN_TOPIC}" 2>/dev/null || true
gcloud pubsub subscriptions create "${FORBIDDEN_SUB}" --topic="${FORBIDDEN_TOPIC}" 2>/dev/null || true

# ---------- 6. Grant SA: bucket read + topic publish + logging write ----------
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/storage.objectViewer"

gcloud pubsub topics add-iam-policy-binding "${FORBIDDEN_TOPIC}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/logging.logWriter"

# ---------- 7. Grant SA: subscription pull + bucket write (for subscriber VM) ----------
gcloud pubsub subscriptions add-iam-policy-binding "${FORBIDDEN_SUB}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/pubsub.subscriber"

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_WEB_EMAIL}" \
  --role="roles/storage.objectUser"

# ---------- 8. Reserve static IP for VM1 ----------
gcloud compute addresses create "${STATIC_IP_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" 2>/dev/null || true

export WEB_STATIC_IP
WEB_STATIC_IP="$(gcloud compute addresses describe "${STATIC_IP_NAME}" --region="${REGION}" --format='get(address)')"

# ---------- 9. Create VM1 (web server): e2-micro, static IP, startup script ----------
# NOTE: This path is relative to hw4/ because the grader runs from repo/hw4.
gcloud compute instances create "${VM_WEB_NAME}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type=e2-micro \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default,address="${WEB_STATIC_IP}" \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account="${SA_WEB_EMAIL}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags=http-server,https-server \
  --create-disk=auto-delete=yes,boot=yes,device-name="${VM_WEB_NAME}",image=projects/ubuntu-os-cloud/global/images/ubuntu-minimal-2510-questing-amd64-v20260225,mode=rw,size=10,type=pd-balanced \
  --metadata-from-file startup-script=startup.sh

# ---------- 10. Create VM2 (client) ----------
gcloud compute instances create "${VM_CLIENT_NAME}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type=e2-micro \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --tags=http-server,https-server \
  --create-disk=auto-delete=yes,boot=yes,device-name="${VM_CLIENT_NAME}",image=projects/ubuntu-os-cloud/global/images/ubuntu-minimal-2510-questing-amd64-v20260225,mode=rw,size=10,type=pd-balanced

# ---------- 11. Create VM3 (forbidden-country subscriber), startup script ----------
# NOTE: Path is relative to hw4/.
gcloud compute instances create "${VM_SUB_NAME}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type=e2-micro \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account="${SA_WEB_EMAIL}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --create-disk=auto-delete=yes,boot=yes,device-name="${VM_SUB_NAME}",image=projects/ubuntu-os-cloud/global/images/ubuntu-minimal-2510-questing-amd64-v20260225,mode=rw,size=10,type=pd-balanced \
  --metadata-from-file startup-script=second_service/startup-subscriber.sh

echo "HW4 setup complete."
echo "VM1 (web server) static IP: ${WEB_STATIC_IP}"

