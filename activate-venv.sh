#!/bin/bash
# Activate virtual environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: ./setup-venv.sh"
    exit 1
fi

source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""
echo "You can now run:"
echo "  python3 ui/app.py              # Start web UI"
echo "  python3 scripts/improve-code.py # Improve code"
echo "  python3 tests/test_connection.py # Test connection"
echo ""
