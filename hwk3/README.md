# hwk3 — File-serving microservice (Cloud Run)

HTTP microservice that serves files from your GCS bucket (same bucket as hwk2). Run it as a **separate service account** with access to the bucket and publish permission on your Pub/Sub channel.

## Behavior

- **GET** with path → object name: returns the file from the bucket with **200 OK** and appropriate `Content-Type`.
- **Non-existent file** → **404 Not Found**. Logged to Cloud Logging via structured logs (JSON) and a simple print.
- **Other methods** (PUT, POST, DELETE, HEAD, CONNECT, OPTIONS, TRACE, PATCH) → **501 Not Implemented**. Logged to Cloud Logging via structured logs and a simple print.

URL path maps to the GCS object name (e.g. `GET /web/page.html` → `gs://BUCKET/web/page.html`).

## Configuration

- **BUCKET** — GCS bucket name (default: `jweb-content`, same as hwk2).

Set when deploying or in Cloud Run config, and for local runs:

```bash
export BUCKET=jweb-content
```

## Local dev

**1. Auth so the app can read GCS**

Use Application Default Credentials (e.g. your user or a key):

```bash
gcloud auth application-default login
# or, with a service account key:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

**2. Install deps and start the server**

```bash
cd hwk3
pip install -r requirements.txt
# or with uv:
# uv pip install -r requirements.txt && uv run functions-framework --target=handler --debug
export BUCKET=jweb-content   # optional if that's already your default
python -m functions_framework --target=handler --debug
```

Server listens on **http://localhost:8080** (or the port printed).

**3. Test with curl**

- **200 OK** — GET a path that exists in the bucket (e.g. a file under `web/` from hwk2):

  ```bash
  curl -i http://localhost:8080/web/yourfile.html
  ```

- **404 Not Found** — GET a path with no object:

  ```bash
  curl -i http://localhost:8080/web/nonexistent.html
  ```

- **501 Not Implemented** — use a non-GET method:

  ```bash
  curl -i -X POST http://localhost:8080/web/yourfile.html
  curl -i -X PUT  http://localhost:8080/
  ```

Check the terminal where the framework is running for structured logs (JSON lines) and print output.

## Deploy

Run these from your project root or anywhere you have `gcloud` configured. Set variables first, then create the service account and permissions, then deploy from `hwk3/`.

**1. Set variables**

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export BUCKET_NAME=jweb-content
export TOPIC_NAME=jweb-events
export SERVICE_NAME=jweb-file-server
export SA_NAME=jweb-file-server-sa
export SA_EMAIL=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
```

**2. Enable APIs** (if not already)

```bash
gcloud services enable run.googleapis.com storage.googleapis.com pubsub.googleapis.com
```

**3. Create the service account**

```bash
gcloud iam service-accounts create ${SA_NAME} \
  --display-name="jweb file server (bucket + pubsub)"
```

**4. Create Pub/Sub topic** (if you don’t have one yet)

```bash
gcloud pubsub topics create ${TOPIC_NAME}
```

**5. Grant bucket read and Pub/Sub publish**

```bash
# Read objects in the bucket
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"

# Publish to the topic
gcloud pubsub topics add-iam-policy-binding ${TOPIC_NAME} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.publisher"
```

**6. Deploy the function**

From the **hwk3** directory. The entry point must be `handler` (the function name in `main.py`); the runtime looks for that function, not `app`.

```bash
cd hwk3

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
  --set-env-vars="BUCKET=${BUCKET_NAME}"
```
