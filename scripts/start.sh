#!/usr/bin/env bash
set -e
source .venv/bin/activate 2>/dev/null || true
export PYTHONPATH=.
echo "Starting Mercurius Web Dashboard and API Server on port 8000..."
python3 -m mercury.ui.server
