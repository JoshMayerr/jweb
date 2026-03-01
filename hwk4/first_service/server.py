"""
HW4 first service: HTTP server (stdlib http.server.HTTPServer + BaseHTTPRequestHandler).
Serves files from GCS; 404/501 -> WARNING; forbidden country -> CRITICAL + Pub/Sub.
"""

import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from google.cloud import storage
from google.cloud import pubsub_v1
import google.cloud.logging

BUCKET_NAME = os.environ.get("BUCKET", "jweb-content")
FORBIDDEN_TOPIC = os.environ.get("FORBIDDEN_TOPIC", "jweb-forbidden")
PORT = int(os.environ.get("PORT", "8080"))

UNSUPPORTED_METHODS = {"PUT", "POST", "DELETE", "HEAD", "CONNECT", "OPTIONS", "TRACE", "PATCH"}

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

# Cloud Logging client and logger (initialized on first use)
_logger = None


def _get_logger():
    global _logger
    if _logger is None:
        client = google.cloud.logging.Client()
        _logger = client.logger("jweb-file-server")
    return _logger


def _log(severity: str, message: str, **fields) -> None:
    """Emit to Cloud Logging with given severity (WARNING, CRITICAL, etc.)."""
    payload = {"message": message, **fields}
    _get_logger().log_struct(payload, severity=severity)
    print(json.dumps({"severity": severity, **payload}), file=sys.stderr)


def _publish_forbidden_event(country: str, path: str, object_name: str) -> None:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not project_id:
        _log("WARNING", "Skipping publish: GOOGLE_CLOUD_PROJECT not set", country=country, path=path)
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
        publisher.publish(topic_path, payload).result()
    except Exception as e:
        _log("ERROR", f"Failed to publish forbidden event: {e}", country=country, path=path)


class GCSFileHandler(BaseHTTPRequestHandler):
    def _send_error_response(self, code: int, short: str, body: bytes = b"") -> None:
        """Send a proper HTTP error response (404, 501, etc.) without using send_error()."""
        self.send_response(code, short)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_501(self, method: str) -> None:
        self._send_error_response(501, "Not Implemented", f"Method {method} not implemented".encode())
        try:
            _log("WARNING", f"Request method not implemented: {method}", status=501, method=method)
        except Exception:
            pass

    def do_GET(self) -> None:
        path = (self.path or "").split("?")[0].strip()
        object_name = path.lstrip("/")

        # X-country: export restriction check
        x_country = (self.headers.get("X-country") or "").strip().lower()
        if x_country and x_country in FORBIDDEN_COUNTRIES:
            obj = object_name or "(root)"
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Permission denied")
            try:
                _log("CRITICAL", f"Forbidden request from restricted country: {x_country}", status=400, country=x_country, path=path, object_name=obj)
                _publish_forbidden_event(x_country, path, obj)
            except Exception:
                pass
            return

        if not object_name or ".." in object_name:
            self._send_error_response(404, "Not Found", b"Not Found")
            try:
                _log("WARNING", f"File not found (invalid path): {path}", status=404, path=path)
            except Exception:
                pass
            return

        try:
            client = storage.Client()
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob(object_name)
        except Exception as e:
            self._send_error_response(500, "Internal Server Error", b"Internal Server Error")
            try:
                _log("ERROR", f"GCS error: {e}", path=path, object_name=object_name)
            except Exception:
                pass
            return

        if not blob.exists():
            self._send_error_response(404, "Not Found", b"Not Found")
            try:
                _log("WARNING", f"File not found: {object_name}", status=404, path=path, object_name=object_name)
            except Exception:
                pass
            return

        try:
            content = blob.download_as_bytes()
        except Exception as e:
            self._send_error_response(500, "Internal Server Error", b"Internal Server Error")
            try:
                _log("ERROR", f"Failed to download: {e}", path=path, object_name=object_name)
            except Exception:
                pass
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_PUT(self) -> None:
        self._send_501("PUT")

    def do_POST(self) -> None:
        self._send_501("POST")

    def do_DELETE(self) -> None:
        self._send_501("DELETE")

    def do_HEAD(self) -> None:
        self._send_501("HEAD")

    def do_CONNECT(self) -> None:
        self._send_501("CONNECT")

    def do_OPTIONS(self) -> None:
        self._send_501("OPTIONS")

    def do_TRACE(self) -> None:
        self._send_501("TRACE")

    def do_PATCH(self) -> None:
        self._send_501("PATCH")

    def log_message(self, format: str, *args) -> None:
        """Suppress default request logging to avoid duplicate/verbose logs."""
        pass


def main() -> None:
    server = HTTPServer(("0.0.0.0", PORT), GCSFileHandler)
    print(f"Serving on 0.0.0.0:{PORT}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
