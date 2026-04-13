#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google.cloud import storage


BUCKET_NAME = os.environ.get("BUCKET", "jweb-content")
PORT = int(os.environ.get("PORT", "80"))
ZONE_HEADER = os.environ.get("ZONE_HEADER", "X-Zone")
ZONE_FALLBACK = os.environ.get("ZONE", "unknown")
HEALTH_PATH = os.environ.get("HEALTH_PATH", "/healthz")

_storage_client: storage.Client | None = None
_zone_name: str | None = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def detect_zone() -> str:
    global _zone_name
    if _zone_name is not None:
        return _zone_name

    metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/zone"
    request = urllib.request.Request(metadata_url, headers={"Metadata-Flavor": "Google"})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            zone_path = response.read().decode("utf-8").strip()
        _zone_name = zone_path.rsplit("/", 1)[-1] or ZONE_FALLBACK
    except (urllib.error.URLError, TimeoutError, OSError):
        _zone_name = ZONE_FALLBACK
    return _zone_name


def get_file_bytes(object_name: str) -> bytes | None:
    if not object_name or ".." in object_name:
        return None
    bucket = get_storage_client().bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)
    if not blob.exists():
        return None
    return blob.download_as_bytes()


class GCSFileHandler(BaseHTTPRequestHandler):
    server_version = "HW8FileServer/1.0"

    def do_GET(self) -> None:
        path = (self.path or "").split("?", 1)[0].strip()
        zone = detect_zone()

        if path == HEALTH_PATH:
            body = f"ok {zone}\n".encode("utf-8")
            self._send_response(200, body, "text/plain; charset=utf-8", zone)
            return

        object_name = path.lstrip("/")
        if not object_name:
            self._send_response(404, b"Not Found", "text/plain; charset=utf-8", zone)
            return

        try:
            content = get_file_bytes(object_name)
        except Exception as exc:  # pragma: no cover
            print(f"Failed to read {object_name} from GCS: {exc}", file=sys.stderr, flush=True)
            self._send_response(500, b"Internal Server Error", "text/plain; charset=utf-8", zone)
            return

        if content is None:
            self._send_response(404, b"Not Found", "text/plain; charset=utf-8", zone)
            return

        self._send_response(200, content, "text/html; charset=utf-8", zone)

    def _send_response(self, status: int, body: bytes, content_type: str, zone: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header(ZONE_HEADER, zone)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(
            f"{self.address_string()} - {self.command} {self.path} -> {format % args} [{detect_zone()}]",
            file=sys.stderr,
            flush=True,
        )


def main() -> None:
    zone = detect_zone()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), GCSFileHandler)
    print(f"Serving on 0.0.0.0:{PORT} in zone {zone}", file=sys.stderr, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
