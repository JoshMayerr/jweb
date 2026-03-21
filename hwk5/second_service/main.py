"""
HW5 second service: same behavior as HW4.
Pulls forbidden-request events from Pub/Sub, prints to stdout, appends to GCS log file.
"""

import json
import os
import sys

from google.cloud import pubsub_v1, storage

BUCKET_NAME = os.environ.get("BUCKET", "jweb-content")
LOG_PATH = "forbidden-logs/forbidden_requests.log"
SUBSCRIPTION_ID = os.environ.get("FORBIDDEN_SUBSCRIPTION", "jweb-forbidden-sub")


def get_project_id() -> str:
    pid = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not pid:
        print("Set GOOGLE_CLOUD_PROJECT or GCP_PROJECT.", file=sys.stderr)
        sys.exit(1)
    return pid


def append_to_gcs_log(line: str) -> None:
    if not (BUCKET_NAME and BUCKET_NAME.strip()):
        return
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(LOG_PATH)
    existing = b""
    if blob.exists():
        existing = blob.download_as_bytes()
    new_content = existing + (line.rstrip() + "\n").encode("utf-8")
    blob.upload_from_string(new_content, content_type="text/plain")


def process_message(data: bytes) -> None:
    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception:
        payload = {"raw": data.decode("utf-8", errors="replace")}
    country = payload.get("country", "?")
    path = payload.get("path", "?")
    object_name = payload.get("object_name", "?")
    timestamp = payload.get("timestamp", "?")
    msg = f"Forbidden request from country={country} path={path} object_name={object_name} at {timestamp}"
    print(msg, flush=True)
    append_to_gcs_log(msg)


def run() -> None:
    project_id = get_project_id()
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, SUBSCRIPTION_ID)

    print(f"Listening on subscription {SUBSCRIPTION_ID} (project {project_id}).", file=sys.stderr)

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            process_message(message.data)
        except Exception as exc:
            print(f"Error processing message: {exc}", file=sys.stderr)
        message.ack()

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()


if __name__ == "__main__":
    run()
