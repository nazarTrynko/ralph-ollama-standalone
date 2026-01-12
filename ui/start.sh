#!/bin/bash
# Quick start script for the Ollama UI

cd "$(dirname "$0")/.."

echo "🚀 Starting Ralph Ollama UI..."
echo ""
echo "Make sure Ollama is running:"
echo "  ollama serve"
echo ""
echo "Then open: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 ui/app.py
