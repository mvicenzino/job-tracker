#!/usr/bin/env python3
"""Run the Job Hunt Tracker web server."""
import argparse
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.web.app import run_server


def main():
    parser = argparse.ArgumentParser(description='Run Job Hunt Tracker web server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--db', help='Path to database file')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    print(f"""
╔═══════════════════════════════════════════════════════╗
║           🎯 Job Hunt Tracker                         ║
╠═══════════════════════════════════════════════════════╣
║  Server running at: http://{args.host}:{args.port}            ║
║  Press Ctrl+C to stop                                 ║
╚═══════════════════════════════════════════════════════╝
    """)

    run_server(
        db_path=args.db,
        host=args.host,
        port=args.port,
        debug=args.debug
    )


if __name__ == '__main__':
    main()
