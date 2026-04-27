#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google.cloud import logging as cloud_logging
from google.cloud import pubsub_v1, storage


BUCKET_NAME = os.environ.get("BUCKET", "jweb-content")
PORT = int(os.environ.get("PORT", "8080"))
LOG_NAME = os.environ.get("LOG_NAME", "hw9-web")
FORBIDDEN_TOPIC = os.environ.get("FORBIDDEN_TOPIC", "jweb-forbidden")
COUNTRY_HEADER = os.environ.get("COUNTRY_HEADER", "X-country")
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")

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

_storage_client: storage.Client | None = None
_logger: cloud_logging.logger.Logger | None = None
_publisher: pubsub_v1.PublisherClient | None = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def get_logger() -> cloud_logging.logger.Logger | None:
    global _logger
    if _logger is not None:
        return _logger
    try:
        client = cloud_logging.Client()
        _logger = client.logger(LOG_NAME)
    except Exception as exc:  # pragma: no cover
        print(f"Failed to initialize Cloud Logging: {exc}", file=sys.stderr, flush=True)
        _logger = None
    return _logger


def log_event(severity: str, message: str, **fields: object) -> None:
    payload = {"message": message, **fields}
    logger = get_logger()
    if logger is not None:
        try:
            logger.log_struct(payload, severity=severity)
        except Exception as exc:  # pragma: no cover
            print(f"Cloud Logging write failed: {exc}", file=sys.stderr, flush=True)
    print(json.dumps({"severity": severity, **payload}), file=sys.stderr, flush=True)


def get_publisher() -> pubsub_v1.PublisherClient:
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
    return _publisher


def publish_forbidden_event(country: str, path: str, object_name: str) -> None:
    if not PROJECT_ID:
        log_event(
            "WARNING",
            "Skipping forbidden publish because project id is not set",
            country=country,
            path=path,
            object_name=object_name,
        )
        return

    payload = json.dumps(
        {
            "country": country,
            "path": path,
            "object_name": object_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ).encode("utf-8")
    topic_path = get_publisher().topic_path(PROJECT_ID, FORBIDDEN_TOPIC)
    get_publisher().publish(topic_path, payload).result(timeout=10)


def get_file_bytes(object_name: str) -> bytes | None:
    if not object_name or ".." in object_name:
        return None
    bucket = get_storage_client().bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)
    if not blob.exists():
        return None
    return blob.download_as_bytes()


def guess_content_type(object_name: str) -> str:
    guessed, _ = mimetypes.guess_type(object_name)
    return guessed or "text/html; charset=utf-8"


class GCSFileHandler(BaseHTTPRequestHandler):
    server_version = "HW9FileServer/1.0"

    def do_GET(self) -> None:
        path = (self.path or "").split("?", 1)[0].strip()
        object_name = path.lstrip("/")
        country = (self.headers.get(COUNTRY_HEADER) or "").strip().lower()

        if country in FORBIDDEN_COUNTRIES:
            object_label = object_name or "(root)"
            try:
                publish_forbidden_event(country, path, object_label)
                log_event(
                    "WARNING",
                    "Forbidden request published to monitor app",
                    status=400,
                    country=country,
                    path=path,
                    object_name=object_label,
                )
            except Exception as exc:  # pragma: no cover
                log_event(
                    "ERROR",
                    "Failed to publish forbidden request",
                    country=country,
                    path=path,
                    object_name=object_label,
                    error=str(exc),
                )
            self._send_response(400, b"Permission denied", "text/plain; charset=utf-8")
            return

        if not object_name or ".." in object_name:
            log_event("WARNING", "404 not found", status=404, path=path)
            self._send_response(404, b"Not Found", "text/plain; charset=utf-8")
            return

        try:
            content = get_file_bytes(object_name)
        except Exception as exc:  # pragma: no cover
            log_event(
                "ERROR",
                "Failed to read object from GCS",
                status=500,
                path=path,
                object_name=object_name,
                error=str(exc),
            )
            self._send_response(500, b"Internal Server Error", "text/plain; charset=utf-8")
            return

        if content is None:
            log_event("WARNING", "404 not found", status=404, path=path, object_name=object_name)
            self._send_response(404, b"Not Found", "text/plain; charset=utf-8")
            return

        self._send_response(200, content, guess_content_type(object_name))

    def _send_501(self, method: str) -> None:
        log_event("WARNING", "501 not implemented", status=501, method=method, path=self.path)
        self._send_response(501, f"Method {method} not implemented".encode("utf-8"), "text/plain; charset=utf-8")

    def _send_response(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

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
        print(
            f"{self.address_string()} - {self.command} {self.path} -> {format % args}",
            file=sys.stderr,
            flush=True,
        )


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), GCSFileHandler)
    print(f"Serving on 0.0.0.0:{PORT} with bucket={BUCKET_NAME}", file=sys.stderr, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
