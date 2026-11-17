#!/usr/bin/env bash
set -e
echo "=== Installing Mercurius Agentic AI System (Python) ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
mkdir -p data/{memory,skills,trajectories,uploads,logs}
echo "=== Installation Complete! Run './scripts/start.sh' to begin ==="
