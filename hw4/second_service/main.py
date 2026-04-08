"""
HW4 second service: runs on VM3.
Pulls forbidden-request events from Pub/Sub, prints to stdout, appends to GCS log file.
Uses VM service account (no key file needed when run on GCE).
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
    if not pid and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        )
        if creds.project_id:
            return creds.project_id
    if not pid:
        print("Set GOOGLE_CLOUD_PROJECT or GCP_PROJECT (or use a key file with project_id).", file=sys.stderr)
        sys.exit(1)
    return pid


def append_to_gcs_log(line: str) -> None:
    """Append a line to the GCS log file (read-modify-write)."""
    if not (BUCKET_NAME and BUCKET_NAME.strip()):
        return  # skip GCS when BUCKET is unset to avoid client errors
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
    if not BUCKET_NAME or BUCKET_NAME.strip() == "":
        print("WARNING: BUCKET env is not set; GCS log append will fail. Set BUCKET to your bucket name.", file=sys.stderr)
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, SUBSCRIPTION_ID)

    try:
        sub = subscriber.get_subscription(request={"subscription": subscription_path})
        topic_name = sub.topic.split("/")[-1] if sub.topic else "?"
        print(f"Subscription OK; topic: {topic_name}", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: Could not get subscription (check name and IAM): {e}", file=sys.stderr)

    print(f"Listening on subscription {SUBSCRIPTION_ID} (project {project_id}). Ctrl+C to stop.", file=sys.stderr)
    print("Forbidden requests will be printed below and appended to gs://" + BUCKET_NAME + "/" + LOG_PATH, file=sys.stderr)

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            process_message(message.data)
        except Exception as e:
            print(f"Error processing message: {e}", file=sys.stderr)
        message.ack()

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()


if __name__ == "__main__":
    run()
