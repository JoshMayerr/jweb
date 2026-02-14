# First service — Cloud Function (file server + X-country)

Serves files from GCS; returns 400 for requests with `X-country` from forbidden countries and publishes those events to Pub/Sub. See [../README.md](../README.md) for behavior and config.

## CLI: Create service account and deploy

Run from anywhere you have `gcloud` configured. The same SA is used by the second service (see [../second_service/README.md](../second_service/README.md)).

**1. Set variables**

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export BUCKET_NAME=jweb-content
export FORBIDDEN_TOPIC=jweb-forbidden
export SERVICE_NAME=jweb-file-server
export SA_NAME=jweb-file-server-sa
export SA_EMAIL=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
```

**2. Enable APIs**

```bash
gcloud services enable run.googleapis.com storage.googleapis.com pubsub.googleapis.com
```

**3. Create the service account**

```bash
gcloud iam service-accounts create ${SA_NAME} \
  --display-name="jweb file server (bucket + pubsub)"
```

**4. Create Pub/Sub topic for forbidden events**

```bash
gcloud pubsub topics create ${FORBIDDEN_TOPIC}
```

**5. Grant the SA permissions (first service)**

```bash
# Read objects in the bucket
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"

# Publish to the forbidden topic
gcloud pubsub topics add-iam-policy-binding ${FORBIDDEN_TOPIC} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.publisher"
```

**6. Deploy the Cloud Function**

From this directory (`hwk3/first_service`):

```bash
cd hwk3/first_service

gcloud functions deploy ${SERVICE_NAME} \
  --gen2 \
  --runtime=python312 \
  --region=${REGION} \
  --source=. \
  --entry-point=handler \
  --memory=128Mi \
  --trigger-http \
  --allow-unauthenticated \
  --service-account=${SA_EMAIL} \
  --set-env-vars="BUCKET=${BUCKET_NAME},FORBIDDEN_TOPIC=${FORBIDDEN_TOPIC}"
```

Deploy output gives the function URL. Test with:

```bash
curl -i -H "X-country: Iran" https://YOUR_FUNCTION_URL/web/somefile.html
```
