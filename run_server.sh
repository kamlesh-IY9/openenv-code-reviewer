#!/bin/bash
# Run Code Reviewer Environment Server
cd "$(dirname "$0")"
echo "Starting Code Reviewer Environment..."
echo "Open browser to: http://localhost:7860"
echo "Press Ctrl+C to stop"
python3 server/app.py
