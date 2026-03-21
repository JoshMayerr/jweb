#!/usr/bin/env python3
"""Tiny HTTP server that prints every request to stdout.

Example (terminal 1): python3 print_requests.py --port 8080
Example (terminal 2): ./http-client-mac -d 127.0.0.1 -p 8080 -b none -w none -n 3 -i 10 -r 1
(Omit -s unless your server uses HTTPS.)
"""

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler


class PrintRequestHandler(BaseHTTPRequestHandler):
    server_version = "PrintRequests/1.0"

    def _read_body(self) -> bytes:
        length = self.headers.get("Content-Length")
        if not length:
            return b""
        try:
            n = int(length)
        except ValueError:
            return b""
        return self.rfile.read(n) if n > 0 else b""

    def _send_ok(self) -> None:
        body = b"ok\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self._log_request(b"")
        self._send_ok()

    def do_HEAD(self) -> None:
        self._log_request(b"")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", "3")
        self.end_headers()

    def do_POST(self) -> None:
        body = self._read_body()
        self._log_request(body)
        self._send_ok()

    def do_PUT(self) -> None:
        body = self._read_body()
        self._log_request(body)
        self._send_ok()

    def do_DELETE(self) -> None:
        self._log_request(b"")
        self._send_ok()

    def do_OPTIONS(self) -> None:
        self._log_request(b"")
        self.send_response(204)
        self.end_headers()

    def _log_request(self, body: bytes) -> None:
        print("-" * 60)
        print(f"{self.command} {self.path} {self.request_version}")
        for k, v in self.headers.items():
            print(f"  {k}: {v}")
        if body:
            try:
                text = body.decode("utf-8", errors="replace")
            except Exception:
                text = repr(body)
            print(f"  [body] ({len(body)} bytes)\n{text}")
        print("-" * 60, flush=True)

    def log_message(self, format: str, *args) -> None:
        # Quiet default access log; we print our own.
        pass


def main() -> None:
    p = argparse.ArgumentParser(description="Print incoming HTTP requests.")
    p.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    p.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    args = p.parse_args()
    httpd = HTTPServer((args.host, args.port), PrintRequestHandler)
    print(f"Listening on http://{args.host}:{args.port}/ — Ctrl+C to stop", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
