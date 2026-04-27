#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

from google.cloud import pubsub_v1, storage


SUBSCRIPTION_ID = os.environ.get("FORBIDDEN_SUBSCRIPTION", "jweb-forbidden-sub")
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
BUCKET_NAME = os.environ.get("BUCKET", "jweb-content")
LOG_PATH = os.environ.get("FORBIDDEN_LOG_PATH", "forbidden-logs/forbidden_requests.log")

_storage_client: storage.Client | None = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def append_to_gcs_log(line: str) -> None:
    if not BUCKET_NAME.strip():
        return

    bucket = get_storage_client().bucket(BUCKET_NAME)
    blob = bucket.blob(LOG_PATH)
    existing = b""
    if blob.exists():
        existing = blob.download_as_bytes()
    blob.upload_from_string(existing + f"{line.rstrip()}\n".encode("utf-8"), content_type="text/plain")


def process_message(data: bytes) -> None:
    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception:
        payload = {"raw": data.decode("utf-8", errors="replace")}

    country = payload.get("country", "?")
    path = payload.get("path", "?")
    object_name = payload.get("object_name", "?")
    timestamp = payload.get("timestamp", "?")
    message = f"Forbidden request from country={country} path={path} object_name={object_name} at {timestamp}"
    print(message, flush=True)
    append_to_gcs_log(message)


def main() -> None:
    if not PROJECT_ID:
        print("Set GOOGLE_CLOUD_PROJECT or GCP_PROJECT before starting the monitor app.", file=sys.stderr)
        sys.exit(1)

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)

    print(f"Listening on Pub/Sub subscription {subscription_path}", file=sys.stderr, flush=True)

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            process_message(message.data)
        finally:
            message.ack()

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()


if __name__ == "__main__":
    main()
