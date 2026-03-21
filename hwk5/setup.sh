#!/bin/bash

set -euo pipefail

export PROJECT_ID="${PROJECT_ID:-cs528-jm}"
export ZONE="${ZONE:-us-central1-c}"
export REGION="${REGION:-us-central1}"
export BUCKET_NAME="${BUCKET_NAME:-jweb-content}"
export FORBIDDEN_TOPIC="${FORBIDDEN_TOPIC:-jweb-forbidden}"
export FORBIDDEN_SUB="${FORBIDDEN_SUB:-jweb-forbidden-sub}"
export SA_NAME="${SA_NAME:-jweb-hwk5-sa}"
export SA_EMAIL="${SA_EMAIL:-${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com}"
export VM_WEB_NAME="${VM_WEB_NAME:-jweb-hwk5-web}"
export VM_SUB_NAME="${VM_SUB_NAME:-jweb-hwk5-subscriber}"
export STATIC_IP_NAME="${STATIC_IP_NAME:-jweb-hwk5-web-ip}"
export DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-jweb-hwk5-mysql}"
export DB_NAME="${DB_NAME:-jwebhw5}"
export DB_USER="${DB_USER:-hw5user}"
export DB_PASSWORD="${DB_PASSWORD:-hw5password}"
export DB_TIER="${DB_TIER:-db-f1-micro}"
export DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-hw5password}"
export PORT="${PORT:-80}"
export WEB_MACHINE_TYPE="${WEB_MACHINE_TYPE:-e2-small}"
export SUB_MACHINE_TYPE="${SUB_MACHINE_TYPE:-e2-micro}"
export FUNCTION_NAME="${FUNCTION_NAME:-jweb-hwk5-stop-db}"
export SCHEDULER_JOB_NAME="${SCHEDULER_JOB_NAME:-jweb-hwk5-stop-db-hourly}"
export GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/joshmayerr/jweb.git}"

echo "Using PROJECT_ID=${PROJECT_ID}, ZONE=${ZONE}, REGION=${REGION}"

gcloud config set project "${PROJECT_ID}"
gcloud config set compute/zone "${ZONE}"

gcloud services enable \
  compute.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  logging.googleapis.com \
  sqladmin.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

gcloud compute firewall-rules create allow-jweb-hwk5-http \
  --project="${PROJECT_ID}" \
  --network=default \
  --allow tcp:80 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server \
  --description "HW5 web server" 2>/dev/null || true

gcloud iam service-accounts create "${SA_NAME}" \
  --display-name="jweb HW5 service account" 2>/dev/null || true

gcloud pubsub topics create "${FORBIDDEN_TOPIC}" 2>/dev/null || true
gcloud pubsub subscriptions create "${FORBIDDEN_SUB}" --topic="${FORBIDDEN_TOPIC}" 2>/dev/null || true

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectUser"

gcloud pubsub topics add-iam-policy-binding "${FORBIDDEN_TOPIC}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.publisher"

gcloud pubsub subscriptions add-iam-policy-binding "${FORBIDDEN_SUB}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.admin"

gcloud sql instances create "${DB_INSTANCE_NAME}" \
  --database-version=MYSQL_8_0 \
  --tier="${DB_TIER}" \
  --region="${REGION}" \
  --root-password="${DB_ROOT_PASSWORD}" 2>/dev/null || true

gcloud sql instances patch "${DB_INSTANCE_NAME}" \
  --activation-policy=ALWAYS \
  --quiet

gcloud sql databases create "${DB_NAME}" --instance="${DB_INSTANCE_NAME}" 2>/dev/null || true
gcloud sql users create "${DB_USER}" --instance="${DB_INSTANCE_NAME}" --password="${DB_PASSWORD}" 2>/dev/null || true
gcloud sql users set-password "${DB_USER}" --instance="${DB_INSTANCE_NAME}" --password="${DB_PASSWORD}"

export INSTANCE_CONNECTION_NAME
INSTANCE_CONNECTION_NAME="$(gcloud sql instances describe "${DB_INSTANCE_NAME}" --format='value(connectionName)')"

uv sync --project hwk5/first_service
INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME}" \
DB_NAME="${DB_NAME}" \
DB_USER="${DB_USER}" \
DB_PASSWORD="${DB_PASSWORD}" \
uv run --project hwk5/first_service hwk5/init_db.py

gcloud compute addresses create "${STATIC_IP_NAME}" --region="${REGION}" 2>/dev/null || true
export WEB_STATIC_IP
WEB_STATIC_IP="$(gcloud compute addresses describe "${STATIC_IP_NAME}" --region="${REGION}" --format='get(address)')"

gcloud compute instances create "${VM_WEB_NAME}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type="${WEB_MACHINE_TYPE}" \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default,address="${WEB_STATIC_IP}" \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account="${SA_EMAIL}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags=http-server,https-server \
  --create-disk=auto-delete=yes,boot=yes,image-family=ubuntu-2404-lts-amd64,image-project=ubuntu-os-cloud,size=10,type=pd-balanced \
  --metadata-from-file startup-script=hwk5/first_service/startup-server.sh

gcloud compute instances create "${VM_SUB_NAME}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type="${SUB_MACHINE_TYPE}" \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account="${SA_EMAIL}" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --create-disk=auto-delete=yes,boot=yes,image-family=ubuntu-2404-lts-amd64,image-project=ubuntu-os-cloud,size=10,type=pd-balanced \
  --metadata-from-file startup-script=hwk5/second_service/startup-subscriber.sh

gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --runtime=python312 \
  --region="${REGION}" \
  --source=hwk5/cloud_function \
  --entry-point=stop_cloud_sql \
  --trigger-http \
  --allow-unauthenticated \
  --service-account="${SA_EMAIL}" \
  --set-env-vars=PROJECT_ID="${PROJECT_ID}",INSTANCE_NAME="${DB_INSTANCE_NAME}"

export FUNCTION_URL
FUNCTION_URL="$(gcloud functions describe "${FUNCTION_NAME}" --gen2 --region="${REGION}" --format='value(serviceConfig.uri)')"

gcloud scheduler jobs create http "${SCHEDULER_JOB_NAME}" \
  --location="${REGION}" \
  --schedule="0 * * * *" \
  --uri="${FUNCTION_URL}" \
  --http-method=GET 2>/dev/null || true

gcloud scheduler jobs update http "${SCHEDULER_JOB_NAME}" \
  --location="${REGION}" \
  --schedule="0 * * * *" \
  --uri="${FUNCTION_URL}" \
  --http-method=GET

echo "HW5 setup complete."
echo "Web server IP: ${WEB_STATIC_IP}"
echo "Cloud SQL instance: ${DB_INSTANCE_NAME}"
