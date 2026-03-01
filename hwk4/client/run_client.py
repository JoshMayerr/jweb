#!/usr/bin/env python3
"""
HW4 client for 100-file demo and stress testing.
Run on VM2: requests files from the web server (VM1). Use 1–4 concurrent
processes (e.g. in separate terminals) for the stress test.

Usage:
  python3 run_client.py http://<WEB_STATIC_IP>:8080 -n 100
  python3 run_client.py http://<WEB_STATIC_IP>:8080 -n 100 --paths web/0.html web/1.html ...
"""
import argparse
import sys
import urllib.request
import urllib.error


def main() -> None:
    parser = argparse.ArgumentParser(description="Request files from HW4 web server (100-file demo / stress test).")
    parser.add_argument("base_url", help="Base URL of the web server, e.g. http://1.2.3.4:8080")
    parser.add_argument("-n", "--num", type=int, default=100, help="Number of requests (default 100)")
    parser.add_argument(
        "--paths",
        nargs="*",
        help="Path suffixes (e.g. web/0.html). If not set, uses web/0.html .. web/(num-1).html",
    )
    parser.add_argument(
        "-H", "--header",
        action="append",
        dest="headers",
        metavar="HEADER:value",
        help="Add header (e.g. 'X-country: Iran'). Can be repeated.",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    if args.paths:
        paths = args.paths[: args.num]
    else:
        paths = [f"web/{i}.html" for i in range(args.num)]

    headers = {}
    if args.headers:
        for h in args.headers:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

    ok = 0
    other = 0
    errors = []

    for path in paths:
        url = f"{base}/{path.lstrip('/')}"
        req = urllib.request.Request(url, headers=headers or None)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    ok += 1
                else:
                    other += 1
                    errors.append((path, resp.status))
        except urllib.error.HTTPError as e:
            other += 1
            errors.append((path, e.code))
        except Exception as e:
            other += 1
            errors.append((path, str(e)))

    print(f"200 OK: {ok}", file=sys.stderr)
    print(f"Other/errors: {other}", file=sys.stderr)
    if errors:
        for path, code in errors[:20]:
            print(f"  {path} -> {code}", file=sys.stderr)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more", file=sys.stderr)
    print(f"200 OK: {ok}, Other: {other}")


if __name__ == "__main__":
    main()
