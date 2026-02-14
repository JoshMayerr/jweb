# hwk3 — Two services: file server + forbidden-request logger

Two services under `hwk3/`:

- **First service** (`first_service/`): Cloud Function. Serves files from GCS; checks `X-country` header and returns 400 for forbidden countries; publishes forbidden events to Pub/Sub.
- **Second service** (`second_service/`): Runs on your laptop. Subscribes to Pub/Sub, prints forbidden-request messages to stdout, and appends them to a log file in GCS.

Both use the **same service account** (bucket access + Pub/Sub publish for first; Pub/Sub subscribe + bucket write for second).

**CLI setup and deploy:** Use the README in each service directory.

- **[first_service/README.md](first_service/README.md)** — Create SA, topic, bucket/viewer + publisher permissions, deploy Cloud Function.
- **[second_service/README.md](second_service/README.md)** — Create subscription, subscriber + bucket writer for SA, create SA key, run locally.

## Directory layout

```
hwk3/
├── README.md           # This file
├── PLAN.md             # Implementation plan
├── first_service/      # Cloud Function: GET files, X-country check, Pub/Sub publish
│   ├── README.md       # CLI: SA, permissions, deploy
│   ├── main.py
│   └── requirements.txt
└── second_service/     # Local: Pub/Sub subscribe, stdout + GCS log (Option A auth)
    ├── README.md       # CLI: subscription, permissions, key, run
    ├── main.py
    └── requirements.txt
```

---

## First service (file server + export check)

**Behavior:** GET with path → file from GCS (200). If `X-country` is a forbidden country (North Korea, Iran, Cuba, Myanmar, Iraq, Libya, Sudan, Zimbabwe, Syria) → 400 and publish to Pub/Sub. Non-existent file → 404. Other methods → 501.

**Config:** `BUCKET`, `FORBIDDEN_TOPIC`. **Local run:** `cd first_service && pip install -r requirements.txt && python -m functions_framework --target=handler --debug` (set env vars). **Deploy:** see [first_service/README.md](first_service/README.md).

---

## Second service (forbidden-request logger, runs on laptop)

**Behavior:** Pulls from Pub/Sub subscription; for each message, prints to stdout and appends to `gs://BUCKET/forbidden-logs/forbidden_requests.log`.

**Auth: Option A — Service account key.** Create a JSON key for the SA, set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`. Client libraries use the key to obtain SA tokens. Chosen for explicit SA identity (no `gcloud auth application-default login`), portability, and no gcloud on the laptop; key must be kept secure and out of the repo.

**Config:** `BUCKET`, `FORBIDDEN_SUBSCRIPTION`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`. **Run:** see [second_service/README.md](second_service/README.md).

---

## Testing

**curl (and provided HTTP client):** GET with `X-country` set to a forbidden country → 400.

```bash
curl -i -H "X-country: Iran" https://YOUR_FUNCTION_URL/web/somefile.html
curl -i https://YOUR_FUNCTION_URL/web/somefile.html
```

With the second service running locally, forbidden requests should appear on stdout and in `gs://BUCKET/forbidden-logs/forbidden_requests.log`.
