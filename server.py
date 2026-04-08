"""
Code Reviewer Environment - Server Entry Point.

This module provides a root-level entry point for the server,
re-exporting from server/app.py for backwards compatibility.
"""

import os

import uvicorn
from server.app import app


def main():
    """Start the Code Reviewer Environment server."""
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
