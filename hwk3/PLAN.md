# Plan: X-country export control + second service (two directories, Option A)

## Directory layout

```
hwk3/
├── README.md                 # Overview, auth explanation, how to run both
├── PLAN.md                   # This file
├── first_service/           # Cloud Function: file server + X-country check + Pub/Sub publish
│   ├── main.py
│   └── requirements.txt
└── second_service/           # Local process: Pub/Sub pull, stdout, GCS append (Option A: SA key)
    ├── main.py               # or runnable script
    └── requirements.txt
```

- **First service** lives in `hwk3/first_service/` (move current `main.py` and `requirements.txt` from `hwk3/` into here; add X-country logic and Pub/Sub publish).
- **Second service** lives in `hwk3/second_service/` (new script that pulls from subscription, prints to stdout, appends to GCS log file). Auth: **Option A — service account key** (see below).

---

## 1. First service (`hwk3/first_service/`)

- **Forbidden countries** (normalized, lowercased): North Korea, Iran, Cuba, Myanmar, Iraq, Libya, Sudan, Zimbabwe, Syria.
- **X-country header:** Read `request.headers.get("X-country", "").strip()`, normalize to lowercase. If in forbidden set → structured log + print, publish JSON message to Pub/Sub topic (e.g. `jweb-forbidden`), return **400** with body e.g. "Permission denied". Otherwise continue with existing flow (path → GCS → 200 or 404/501).
- **Config:** Env `BUCKET`, `FORBIDDEN_TOPIC` (or reuse existing topic name).
- **Dependencies:** `functions-framework`, `google-cloud-storage`, `google-cloud-pubsub`.
- **Deploy:** From `hwk3/first_service/`: `gcloud functions deploy ... --source=. --entry-point=handler` and set env vars including `FORBIDDEN_TOPIC`.

---

## 2. Pub/Sub

- **Topic:** e.g. `jweb-forbidden` for forbidden-request events. First service SA needs `roles/pubsub.publisher` on it.
- **Subscription:** Pull subscription (e.g. `jweb-forbidden-sub`) for second service. Same SA needs `roles/pubsub.subscriber` on the subscription.

---

## 3. Second service (`hwk3/second_service/`)

- **Runs on laptop.** Loop: pull from pull subscription → for each message: print error to stdout, append line to GCS file `gs://BUCKET/forbidden-logs/forbidden_requests.log` (read blob if exists, append new line, write back).
- **Auth: Option A — Service account key.** Create a JSON key for the same SA, store securely (not in repo). Run with `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`. Document in README: how it works (client libraries use the key to obtain SA tokens), why chosen (explicit SA identity, no gcloud, works everywhere; key must be protected).
- **Dependencies:** `google-cloud-pubsub`, `google-cloud-storage`.
- **Config:** Env `BUCKET`, `GOOGLE_APPLICATION_CREDENTIALS`, project/subscription ID (env or args).

---

## 4. SA permissions

- **First service (unchanged):** `roles/storage.objectViewer`, `roles/pubsub.publisher` on the forbidden topic.
- **Second service (same SA):** `roles/pubsub.subscriber` on the pull subscription; `roles/storage.objectUser` on the bucket (to write/append under `forbidden-logs/`).

---

## 5. Testing

- **curl:** `curl -i -H "X-country: Iran" https://FUNCTION_URL/web/somefile.html` → 400. Same for other forbidden countries. Without header or allowed country → 200.
- **Provided HTTP client:** Use it with X-country set to forbidden countries; confirm 400.
- **Second service:** Run locally with key; trigger forbidden requests; verify stdout and appended lines in `gs://BUCKET/forbidden-logs/forbidden_requests.log`.

---

## 6. README

- **hwk3/README.md:** Describe both services, directory layout, X-country behavior, 400 for forbidden, Pub/Sub flow. For second service: **Option A** — use SA key and `GOOGLE_APPLICATION_CREDENTIALS`; explain how it works (key → tokens) and why chosen (explicit SA, portable, no gcloud ADC). How to run first (local + deploy) and second (local only). Curl and provided-client testing.

---

## Implementation order

1. Create `hwk3/first_service/` and move existing `main.py` + `requirements.txt` from `hwk3/` into it; add forbidden list, X-country check, Pub/Sub publish, 400 response.
2. Create Pub/Sub topic and pull subscription; grant SA publish + subscribe and `storage.objectUser`.
3. Create `hwk3/second_service/` with script, requirements, and Option A auth; document in README.
4. Update root `hwk3/README.md` with layout, Option A explanation, and test commands.
5. Remove or redirect old top-level `hwk3/main.py` and `hwk3/requirements.txt` (replaced by first_service).
