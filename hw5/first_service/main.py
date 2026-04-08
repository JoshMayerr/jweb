import atexit
import json
import os
import signal
import sys
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter

import google.cloud.logging
from google.cloud import pubsub_v1, storage
from google.cloud.sql.connector import Connector
import pymysql

BUCKET_NAME = os.environ.get("BUCKET", "jweb-content")
FORBIDDEN_TOPIC = os.environ.get("FORBIDDEN_TOPIC", "jweb-forbidden")
PORT = int(os.environ.get("PORT", "80"))
DB_INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME", "")
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "")
TIMING_LOG_INTERVAL = int(os.environ.get("TIMING_LOG_INTERVAL", "1000"))

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

_logger = None
_storage_client = None
_publisher = None
_connector = None


@dataclass
class RequestMetadata:
    country: str
    client_ip: str
    gender: str
    age_group: str
    income_group: str
    is_banned: bool
    request_time: datetime
    time_of_day: str
    requested_file: str


class TimingStats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0
        self._totals = {
            "header_extract_seconds": 0.0,
            "gcs_read_seconds": 0.0,
            "response_send_seconds": 0.0,
            "db_insert_seconds": 0.0,
        }

    def record(self, name: str, elapsed_seconds: float) -> None:
        with self._lock:
            self._totals[name] += elapsed_seconds

    def finish_request(self) -> None:
        should_report = False
        with self._lock:
            self._count += 1
            should_report = self._count % max(TIMING_LOG_INTERVAL, 1) == 0
        if should_report:
            self.print_summary(prefix=f"timing summary after {self.request_count} requests")

    @property
    def request_count(self) -> int:
        with self._lock:
            return self._count

    def snapshot(self) -> tuple[int, dict[str, float]]:
        with self._lock:
            return self._count, dict(self._totals)

    def print_summary(self, prefix: str = "final timing summary") -> None:
        count, totals = self.snapshot()
        if count == 0:
            print(f"{prefix}: no requests processed", file=sys.stderr, flush=True)
            return
        averages = {name: total / count for name, total in totals.items()}
        payload = {
            "requests": count,
            "totals": totals,
            "averages": averages,
        }
        print(f"{prefix}: {json.dumps(payload, sort_keys=True)}", file=sys.stderr, flush=True)


TIMING_STATS = TimingStats()


def _handle_exit(signum, frame) -> None:  # type: ignore[no-untyped-def]
    TIMING_STATS.print_summary(prefix=f"timing summary before signal {signum}")
    raise SystemExit(0)


signal.signal(signal.SIGTERM, _handle_exit)
signal.signal(signal.SIGINT, _handle_exit)
atexit.register(TIMING_STATS.print_summary)


def _get_logger():
    global _logger
    if _logger is None:
        client = google.cloud.logging.Client()
        _logger = client.logger("jweb-file-server")
    return _logger


def _log(severity: str, message: str, **fields) -> None:
    payload = {"message": message, **fields}
    _get_logger().log_struct(payload, severity=severity)
    print(json.dumps({"severity": severity, **payload}), file=sys.stderr, flush=True)


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def get_publisher() -> pubsub_v1.PublisherClient:
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
    return _publisher


def get_connector() -> Connector | None:
    global _connector
    if not all([DB_INSTANCE_CONNECTION_NAME, DB_USER, DB_PASSWORD, DB_NAME]):
        return None
    if _connector is None:
        _connector = Connector()
    return _connector


def get_db_connection():
    connector = get_connector()
    if connector is None:
        return None
    return connector.connect(
        DB_INSTANCE_CONNECTION_NAME,
        "pymysql",
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
    )


def parse_request_time(raw_value: str) -> datetime:
    if raw_value:
        try:
            return datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return datetime.now(tz=UTC).replace(tzinfo=None)


def classify_time_of_day(dt: datetime) -> str:
    hour = dt.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def extract_request_metadata(handler: BaseHTTPRequestHandler) -> RequestMetadata:
    path = (handler.path or "").split("?")[0].strip()
    requested_file = path.lstrip("/") or "(root)"
    country = (handler.headers.get("X-country") or "").strip()
    request_time = parse_request_time((handler.headers.get("X-time") or "").strip())
    return RequestMetadata(
        country=country,
        client_ip=(handler.headers.get("X-client-IP") or "").strip(),
        gender=(handler.headers.get("X-gender") or "").strip(),
        age_group=(handler.headers.get("X-age") or "").strip(),
        income_group=(handler.headers.get("X-income") or "").strip(),
        is_banned=country.lower() in FORBIDDEN_COUNTRIES,
        request_time=request_time,
        time_of_day=classify_time_of_day(request_time),
        requested_file=requested_file,
    )


def fetch_object_from_gcs(object_name: str) -> tuple[int, bytes, str]:
    if not object_name or ".." in object_name:
        return 404, b"Not Found", "text/plain"

    bucket = get_storage_client().bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)
    if not blob.exists():
        return 404, b"Not Found", "text/plain"
    return 200, blob.download_as_bytes(), "text/html"


def send_http_response(
    handler: BaseHTTPRequestHandler,
    status_code: int,
    body: bytes,
    content_type: str,
    status_text: str,
) -> None:
    handler.send_response(status_code, status_text)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    if body:
        handler.wfile.write(body)


def insert_request_log(connection, metadata: RequestMetadata, status_code: int) -> None:
    if connection is None:
        return
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO request_logs (
                country, client_ip, gender, age_group, income_group,
                is_banned, request_time, time_of_day, requested_file, status_code
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                metadata.country,
                metadata.client_ip,
                metadata.gender,
                metadata.age_group,
                metadata.income_group,
                metadata.is_banned,
                metadata.request_time,
                metadata.time_of_day,
                metadata.requested_file,
                status_code,
            ),
        )
    connection.commit()


def insert_error_log(connection, metadata: RequestMetadata, error_code: int) -> None:
    if connection is None:
        return
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO error_logs (request_time, requested_file, error_code)
            VALUES (%s, %s, %s)
            """,
            (metadata.request_time, metadata.requested_file, error_code),
        )
    connection.commit()


def publish_forbidden_event(country: str, path: str, object_name: str) -> None:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not project_id:
        _log("WARNING", "Skipping publish: GOOGLE_CLOUD_PROJECT not set", country=country, path=path)
        return
    payload = json.dumps(
        {
            "country": country,
            "path": path,
            "object_name": object_name,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }
    ).encode("utf-8")
    topic_path = get_publisher().topic_path(project_id, FORBIDDEN_TOPIC)
    get_publisher().publish(topic_path, payload).result()


class GCSFileHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._handle_get()

    def do_PUT(self) -> None:
        self._handle_unsupported_method()

    def do_POST(self) -> None:
        self._handle_unsupported_method()

    def do_DELETE(self) -> None:
        self._handle_unsupported_method()

    def do_HEAD(self) -> None:
        self._handle_unsupported_method()

    def do_CONNECT(self) -> None:
        self._handle_unsupported_method()

    def do_OPTIONS(self) -> None:
        self._handle_unsupported_method()

    def do_TRACE(self) -> None:
        self._handle_unsupported_method()

    def do_PATCH(self) -> None:
        self._handle_unsupported_method()

    def _handle_unsupported_method(self) -> None:
        method = self.command
        start = perf_counter()
        metadata = extract_request_metadata(self)
        TIMING_STATS.record("header_extract_seconds", perf_counter() - start)

        response_start = perf_counter()
        send_http_response(
            self,
            501,
            f"Method {method} not implemented".encode("utf-8"),
            "text/plain",
            "Not Implemented",
        )
        TIMING_STATS.record("response_send_seconds", perf_counter() - response_start)

        db_start = perf_counter()
        self._write_database_rows(metadata, 501)
        TIMING_STATS.record("db_insert_seconds", perf_counter() - db_start)

        _log("WARNING", f"Request method not implemented: {method}", status=501, method=method)
        TIMING_STATS.finish_request()

    def _handle_get(self) -> None:
        path = (self.path or "").split("?")[0].strip()

        header_start = perf_counter()
        metadata = extract_request_metadata(self)
        TIMING_STATS.record("header_extract_seconds", perf_counter() - header_start)

        if metadata.is_banned:
            response_start = perf_counter()
            send_http_response(self, 400, b"Permission denied", "text/plain", "Bad Request")
            TIMING_STATS.record("response_send_seconds", perf_counter() - response_start)

            try:
                _log(
                    "CRITICAL",
                    "Forbidden request from restricted country",
                    status=400,
                    country=metadata.country.lower(),
                    path=path,
                    object_name=metadata.requested_file,
                )
                publish_forbidden_event(metadata.country.lower(), path, metadata.requested_file)
            except Exception as exc:
                _log("ERROR", f"Failed to publish forbidden event: {exc}", path=path)

            db_start = perf_counter()
            self._write_database_rows(metadata, 400)
            TIMING_STATS.record("db_insert_seconds", perf_counter() - db_start)
            TIMING_STATS.finish_request()
            return

        gcs_start = perf_counter()
        try:
            status_code, body, content_type = fetch_object_from_gcs(metadata.requested_file)
            status_text = "OK" if status_code == 200 else "Not Found"
        except Exception as exc:
            status_code, body, content_type, status_text = (
                500,
                b"Internal Server Error",
                "text/plain",
                "Internal Server Error",
            )
            _log("ERROR", f"GCS error: {exc}", path=path, object_name=metadata.requested_file)
        TIMING_STATS.record("gcs_read_seconds", perf_counter() - gcs_start)

        response_start = perf_counter()
        send_http_response(self, status_code, body, content_type, status_text)
        TIMING_STATS.record("response_send_seconds", perf_counter() - response_start)

        db_start = perf_counter()
        self._write_database_rows(metadata, status_code)
        TIMING_STATS.record("db_insert_seconds", perf_counter() - db_start)

        if status_code == 404:
            _log("WARNING", "File not found", status=404, path=path, object_name=metadata.requested_file)
        TIMING_STATS.finish_request()

    def _write_database_rows(self, metadata: RequestMetadata, status_code: int) -> None:
        connection = None
        try:
            connection = get_db_connection()
            insert_request_log(connection, metadata, status_code)
            if status_code != 200:
                insert_error_log(connection, metadata, status_code)
        except Exception as exc:
            _log("ERROR", f"Failed to write database rows: {exc}", status=status_code)
        finally:
            if connection is not None:
                connection.close()

    def log_message(self, format: str, *args) -> None:
        pass


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), GCSFileHandler)
    print(f"Serving on 0.0.0.0:{PORT}", file=sys.stderr, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
