"""HTTP microservice: GET returns file contents from GCS bucket; other methods → 501."""

import json
import os

import functions_framework
from google.cloud import storage

BUCKET_NAME = os.environ.get("BUCKET", "jweb-content")
UNSUPPORTED_METHODS = {"PUT", "POST", "DELETE", "HEAD", "CONNECT", "OPTIONS", "TRACE", "PATCH"}


def _structured_log(level: str, message: str, **fields) -> None:
    """Emit a structured log entry for Cloud Logging and a simple print."""
    entry = {"severity": level, "message": message, **fields}
    print(json.dumps(entry))
    print(message)


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
