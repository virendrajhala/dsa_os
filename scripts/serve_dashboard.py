#!/usr/bin/env python3
"""Serve the static DSA_OS web dashboard from the repository root."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import sys
import webbrowser
from datetime import date
from pathlib import Path

from _shared import build_dashboard_feed, load_repository_state

# Serves the whole repo root (fine for localhost): the dashboard fetches
# data via relative ../progress, ../curriculum, ../knowledge paths.
ROOT = Path(__file__).resolve().parents[1]


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with a quieter request log plus the live feed endpoint."""

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if self.path.split("?", 1)[0].rstrip("/") == "/api/feed":
            self._serve_feed()
            return
        super().do_GET()

    def _serve_feed(self) -> None:
        """GET /api/feed: the dashboard's single source of computed truth,
        built by the same engine the CLI uses. Never crashes the server on bad
        data - a load/compute failure returns 500 with a JSON error body."""

        try:
            state = load_repository_state()
            feed = build_dashboard_feed(state, date.today())
            body = json.dumps(feed).encode("utf-8")
            status = 200
        except Exception as exc:  # noqa: BLE001 - surface, never kill the server
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            status = 500
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
