#!/usr/bin/env python3
"""Standalone entry point for the WoW Toolkit web app.

Usage:
    python run.py                              # run on 127.0.0.1:5060
    python run.py --host 0.0.0.0 --port 5060   # for a reverse proxy that
                                                # can't reach 127.0.0.1 on
                                                # this machine (e.g. Nginx
                                                # Proxy Manager in its own
                                                # Docker container)
"""

import argparse

from app import create_app
from config import DEFAULT_PORT


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WoW Toolkit web app.")
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Interface to bind to (default: 127.0.0.1 -- put this behind "
             "`tailscale serve` rather than binding 0.0.0.0 directly; see "
             "deploy/wow-toolkit-web.service for the alternative).",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable Flask's debug reloader/debugger. Leave off outside active development.",
    )
    args = parser.parse_args()

    app = create_app()
    print(f"WoW Toolkit running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()
