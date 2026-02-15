# Second service — Forbidden-request logger (runs on laptop)

Pulls forbidden-request events from Pub/Sub, prints to stdout, and appends to a log file in GCS. Uses the **same service account** as the first service. See [../README.md](../README.md) for behavior and Option A auth.

## Prerequisite

- **Python 3.12** and **uv** (this directory has its own `pyproject.toml`; uv creates a venv and installs deps—no pip needed).
- The service account and first-service permissions must already exist (see [../first_service/README.md](../first_service/README.md) steps 1–5). You need the SA email (e.g. `jweb-file-server-sa@PROJECT_ID.iam.gserviceaccount.com`).

## CLI: Subscription, SA permissions, key, and run

**1. Set variables** (use same `PROJECT_ID` and `SA_EMAIL` as first service)

```bash
export PROJECT_ID=$(gcloud config get-value project)
export BUCKET_NAME=jweb-content
export FORBIDDEN_TOPIC=jweb-forbidden
export FORBIDDEN_SUB=jweb-forbidden-sub
export SA_NAME=jweb-file-server-sa
export SA_EMAIL=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
```

**2. Create pull subscription for the second service**

```bash
gcloud pubsub subscriptions create ${FORBIDDEN_SUB} \
  --topic=${FORBIDDEN_TOPIC}
```

**3. Grant the SA permission to pull messages**

```bash
gcloud pubsub subscriptions add-iam-policy-binding ${FORBIDDEN_SUB} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.subscriber"
```

**4. Grant the SA permission to write to the bucket** (append log file)

```bash
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectUser"
```

**5. Create a JSON key for the SA** (Option A — run as SA on your laptop)

In GCP Console: IAM & Admin → Service Accounts → select `jweb-file-server-sa` → Keys → Add key → Create new key → JSON. Save the file somewhere secure (e.g. `~/.config/jweb-sa-key.json`) and **do not commit it**.

Or with gcloud:

```bash
gcloud iam service-accounts keys create ~/.config/jweb-sa-key.json \
  --iam-account=${SA_EMAIL}
```

**6. Run the second service locally**

```bash
cd hwk3/second_service
uv sync   # create venv and install deps (uses pyproject.toml)
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/jweb-sa-key.json
export BUCKET=${BUCKET_NAME}
export FORBIDDEN_SUBSCRIPTION=${FORBIDDEN_SUB}
export GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
uv run main.py
```

Forbidden requests will be printed to stdout and appended to `gs://${BUCKET_NAME}/forbidden-logs/forbidden_requests.log`. Ctrl+C to stop.
