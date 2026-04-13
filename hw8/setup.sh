#!/bin/bash

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-cs528-jm}"
REGION="${REGION:-us-central1}"
ZONE_A="${ZONE_A:-us-central1-b}"
ZONE_B="${ZONE_B:-us-central1-c}"
BUCKET_NAME="${BUCKET_NAME:-jweb-content}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-hw8-web-sa}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_EMAIL:-${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com}"
INSTANCE_A="${INSTANCE_A:-hw8-web-a}"
INSTANCE_B="${INSTANCE_B:-hw8-web-b}"
ADDRESS_NAME="${ADDRESS_NAME:-hw8-lb-ip}"
HEALTH_CHECK_NAME="${HEALTH_CHECK_NAME:-hw8-health-check}"
TARGET_POOL_NAME="${TARGET_POOL_NAME:-hw8-target-pool}"
FORWARDING_RULE_NAME="${FORWARDING_RULE_NAME:-hw8-forwarding-rule}"
FIREWALL_RULE_NAME="${FIREWALL_RULE_NAME:-hw8-allow-http}"
HEALTH_FIREWALL_RULE_NAME="${HEALTH_FIREWALL_RULE_NAME:-hw8-allow-health-check}"
TAG_NAME="${TAG_NAME:-hw8-backend}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-micro}"
IMAGE_FAMILY="${IMAGE_FAMILY:-ubuntu-2204-lts}"
IMAGE_PROJECT="${IMAGE_PROJECT:-ubuntu-os-cloud}"
REPO_URL="${REPO_URL:-https://github.com/joshmayerr/jweb.git}"

echo "Setting up HW8 in project ${PROJECT_ID}"
echo "Using zones ${ZONE_A} and ${ZONE_B} in region ${REGION}"

gcloud config set project "${PROJECT_ID}"

gcloud services enable compute.googleapis.com storage.googleapis.com iam.googleapis.com

gcloud compute firewall-rules create "${FIREWALL_RULE_NAME}" \
  --project="${PROJECT_ID}" \
  --network=default \
  --allow=tcp:80 \
  --source-ranges=0.0.0.0/0 \
  --target-tags="${TAG_NAME}" \
  2>/dev/null || true

gcloud compute firewall-rules create "${HEALTH_FIREWALL_RULE_NAME}" \
  --project="${PROJECT_ID}" \
  --network=default \
  --allow=tcp:80 \
  --source-ranges=35.191.0.0/16,130.211.0.0/22 \
  --target-tags="${TAG_NAME}" \
  2>/dev/null || true

gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
  --display-name="HW8 web service account" \
  2>/dev/null || true

sleep 10

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/storage.objectViewer"

gcloud compute addresses create "${ADDRESS_NAME}" \
  --region="${REGION}" \
  2>/dev/null || true

LB_IP="$(gcloud compute addresses describe "${ADDRESS_NAME}" --region="${REGION}" --format='get(address)')"

gcloud compute http-health-checks create "${HEALTH_CHECK_NAME}" \
  --request-path=/healthz \
  --port=80 \
  --check-interval=5 \
  --timeout=5 \
  --healthy-threshold=2 \
  --unhealthy-threshold=2 \
  2>/dev/null || true

gcloud compute instances create "${INSTANCE_A}" \
  --zone="${ZONE_A}" \
  --machine-type="${MACHINE_TYPE}" \
  --image-family="${IMAGE_FAMILY}" \
  --image-project="${IMAGE_PROJECT}" \
  --service-account="${SERVICE_ACCOUNT_EMAIL}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags="${TAG_NAME}" \
  --metadata=PROJECT_ID="${PROJECT_ID}",BUCKET_NAME="${BUCKET_NAME}",REPO_URL="${REPO_URL}",PORT=80 \
  --metadata-from-file=startup-script=startup-web.sh \
  2>/dev/null || true

gcloud compute instances create "${INSTANCE_B}" \
  --zone="${ZONE_B}" \
  --machine-type="${MACHINE_TYPE}" \
  --image-family="${IMAGE_FAMILY}" \
  --image-project="${IMAGE_PROJECT}" \
  --service-account="${SERVICE_ACCOUNT_EMAIL}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags="${TAG_NAME}" \
  --metadata=PROJECT_ID="${PROJECT_ID}",BUCKET_NAME="${BUCKET_NAME}",REPO_URL="${REPO_URL}",PORT=80 \
  --metadata-from-file=startup-script=startup-web.sh \
  2>/dev/null || true

gcloud compute target-pools create "${TARGET_POOL_NAME}" \
  --region="${REGION}" \
  --http-health-check="${HEALTH_CHECK_NAME}" \
  2>/dev/null || true

gcloud compute target-pools add-instances "${TARGET_POOL_NAME}" \
  --instances="${INSTANCE_A}" \
  --instances-zone="${ZONE_A}" \
  2>/dev/null || true

gcloud compute target-pools add-instances "${TARGET_POOL_NAME}" \
  --instances="${INSTANCE_B}" \
  --instances-zone="${ZONE_B}" \
  2>/dev/null || true

gcloud compute forwarding-rules create "${FORWARDING_RULE_NAME}" \
  --region="${REGION}" \
  --ports=80 \
  --address="${LB_IP}" \
  --target-pool="${TARGET_POOL_NAME}" \
  2>/dev/null || true

echo "HW8 setup complete."
echo "Load balancer IP: ${LB_IP}"
echo "Backend A: ${INSTANCE_A} in ${ZONE_A}"
echo "Backend B: ${INSTANCE_B} in ${ZONE_B}"
