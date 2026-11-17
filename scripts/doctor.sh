#!/usr/bin/env bash
# Mercurius Diagnostic Doctor Execution Script
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

export PYTHONPATH="$DIR:$PYTHONPATH"
python3 -m mercury.doctor "$@"
