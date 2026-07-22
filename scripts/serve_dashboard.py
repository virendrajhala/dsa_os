#!/usr/bin/env python3
"""Serve the static DSA_OS web dashboard from the repository root."""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import webbrowser
from pathlib import Path

# Serves the whole repo root (fine for localhost): the dashboard fetches
# data via relative ../progress, ../curriculum, ../knowledge paths.
ROOT = Path(__file__).resolve().parents[1]


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with a quieter request log."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the DSA_OS web dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the dashboard in the default browser.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    handler = functools.partial(DashboardHandler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer((args.host, args.port), handler) as httpd:
            url = f"http://{args.host}:{args.port}/web_dashboard/"
            print(f"DSA_OS dashboard: {url}")
            print("Press Ctrl+C to stop.")
            if args.open:
                webbrowser.open(url)
            httpd.serve_forever()
    except OSError as exc:
        print(f"Could not start dashboard server: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
