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

echo "Cleaning up HW8 resources in project ${PROJECT_ID}"

gcloud config set project "${PROJECT_ID}"

gcloud compute forwarding-rules delete "${FORWARDING_RULE_NAME}" --region="${REGION}" --quiet || true
gcloud compute target-pools delete "${TARGET_POOL_NAME}" --region="${REGION}" --quiet || true
gcloud compute http-health-checks delete "${HEALTH_CHECK_NAME}" --quiet || true

gcloud compute instances delete "${INSTANCE_A}" --zone="${ZONE_A}" --quiet || true
gcloud compute instances delete "${INSTANCE_B}" --zone="${ZONE_B}" --quiet || true

gcloud compute addresses delete "${ADDRESS_NAME}" --region="${REGION}" --quiet || true
gcloud compute firewall-rules delete "${FIREWALL_RULE_NAME}" --quiet || true
gcloud compute firewall-rules delete "${HEALTH_FIREWALL_RULE_NAME}" --quiet || true

gcloud storage buckets remove-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/storage.objectViewer" \
  --quiet || true

gcloud iam service-accounts delete "${SERVICE_ACCOUNT_EMAIL}" --quiet || true

echo "HW8 cleanup complete."
