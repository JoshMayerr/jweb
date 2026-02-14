"""HTTP microservice: GET returns file contents from GCS; X-country export check; other methods → 501."""

import json
import os
from datetime import datetime, timezone

import functions_framework
from google.cloud import storage, pubsub_v1

BUCKET_NAME = os.environ.get("BUCKET", "jweb-content")
FORBIDDEN_TOPIC = os.environ.get("FORBIDDEN_TOPIC", "jweb-forbidden")
UNSUPPORTED_METHODS = {"PUT", "POST", "DELETE", "HEAD", "CONNECT", "OPTIONS", "TRACE", "PATCH"}

# US export-restricted countries (sensitive crypto material); normalized lowercase
FORBIDDEN_COUNTRIES = {
    "north korea",
    "iran",
    "cuba",
    "myanmar",
    "iraq",
    "libya",
    "sudan",
    "zimbabwe",
    "syria",
}


def _structured_log(level: str, message: str, **fields) -> None:
    """Emit a structured log entry for Cloud Logging and a simple print."""
    entry = {"severity": level, "message": message, **fields}
    print(json.dumps(entry))
    print(message)


def _publish_forbidden_event(country: str, path: str, object_name: str) -> None:
    """Publish a forbidden-request event to Pub/Sub for the second service."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not project_id:
        return
    payload = json.dumps({
        "country": country,
        "path": path,
        "object_name": object_name,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }).encode("utf-8")
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, FORBIDDEN_TOPIC)
        publisher.publish(topic_path, payload)
    except Exception as e:
        _structured_log("ERROR", f"Failed to publish forbidden event: {e}", country=country, path=path)


@functions_framework.http
def handler(request):
    method = request.method

    if method in UNSUPPORTED_METHODS:
        _structured_log(
            "WARNING",
            f"Request method not implemented: {method}",
            status=501,
            method=method,
        )
        return "", 501

    if method != "GET":
        _structured_log(
            "WARNING",
            f"Request method not implemented: {method}",
            status=501,
            method=method,
        )
        return "", 501

    # X-country: export restriction check (forbidden countries get 400)
    x_country = (request.headers.get("X-country") or "").strip().lower()
    if x_country and x_country in FORBIDDEN_COUNTRIES:
        path = (request.path or "").strip()
        object_name = path.lstrip("/") or "(root)"
        _structured_log(
            "WARNING",
            f"Forbidden request from restricted country: {x_country}",
            status=400,
            country=x_country,
            path=path,
            object_name=object_name,
        )
        _publish_forbidden_event(x_country, path, object_name)
        return "Permission denied", 400

    path = (request.path or "").strip()
    object_name = path.lstrip("/")
    if not object_name or ".." in object_name:
        _structured_log(
            "WARNING",
            f"File not found (invalid path): {path}",
            status=404,
            path=path,
        )
        return "", 404

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)

    if not blob.exists():
        _structured_log(
            "WARNING",
            f"File not found: {object_name}",
            status=404,
            path=path,
            object_name=object_name,
        )
        return "", 404

    content = blob.download_as_bytes()
    headers = {"Content-Type": "text/html"}

    return content, 200, headers
