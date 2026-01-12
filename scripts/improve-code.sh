#!/bin/bash
# Convenience script to run code improvement

cd "$(dirname "$0")/.."

python3 scripts/improve-code.py "$@"
