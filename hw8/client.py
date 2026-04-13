#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send repeated requests and print the returned zone header.")
    parser.add_argument("--host", required=True, help="Load balancer IP or hostname")
    parser.add_argument("--port", type=int, default=80, help="Server port")
    parser.add_argument("--path", default="/100.html", help="Path to request")
    parser.add_argument("--scheme", default="http", choices=["http", "https"], help="URL scheme")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--count", type=int, default=0, help="Number of requests to send; 0 means forever")
    parser.add_argument("--timeout", type=float, default=5.0, help="Per-request timeout in seconds")
    parser.add_argument("--zone-header", default="X-Zone", help="Header name to print")
    parser.add_argument("--country", default="", help="Optional X-country header")
    return parser.parse_args()


def build_url(args: argparse.Namespace) -> str:
    path = args.path if args.path.startswith("/") else f"/{args.path}"
    return f"{args.scheme}://{args.host}:{args.port}{path}"


def main() -> None:
    args = parse_args()
    url = build_url(args)
    zone_counts: Counter[str] = Counter()
    request_number = 0

    print(f"Sending requests to {url} every {args.interval:.2f}s", flush=True)

    while args.count == 0 or request_number < args.count:
        request_number += 1
        started = time.perf_counter()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        headers = {}
        if args.country:
            headers["X-country"] = args.country
        request = urllib.request.Request(url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                elapsed = time.perf_counter() - started
                zone = response.headers.get(args.zone_header, "missing")
                zone_counts[zone] += 1
                body = response.read()
                print(
                    f"{timestamp} req={request_number} status={response.status} zone={zone} "
                    f"bytes={len(body)} elapsed={elapsed:.3f}s"
                )
        except urllib.error.HTTPError as exc:
            elapsed = time.perf_counter() - started
            zone = exc.headers.get(args.zone_header, "missing")
            zone_counts[zone] += 1
            body = exc.read()
            print(
                f"{timestamp} req={request_number} status={exc.code} zone={zone} "
                f"bytes={len(body)} elapsed={elapsed:.3f}s"
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            print(f"{timestamp} req={request_number} error={type(exc).__name__} detail={exc} elapsed={elapsed:.3f}s")

        sys.stdout.flush()
        time.sleep(max(args.interval, 0.0))

    if zone_counts:
        print("Zone counts:")
        for zone, count in sorted(zone_counts.items()):
            print(f"{zone}: {count}")


if __name__ == "__main__":
    main()
