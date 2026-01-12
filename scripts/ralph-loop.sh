#!/bin/bash

# Ralph Loop Script
# Convenience wrapper to run Ralph loops with cycle control

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_OLLAMA_DIR="$(dirname "$SCRIPT_DIR")"

# Functions
log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if Python script exists
PYTHON_SCRIPT="$SCRIPT_DIR/ralph-loop.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
  log_error "Python script not found: $PYTHON_SCRIPT"
  exit 1
fi

# Check if we're in a virtual environment, activate if needed
if [ -z "$VIRTUAL_ENV" ]; then
  VENV_PATH="$RALPH_OLLAMA_DIR/venv"
  if [ -d "$VENV_PATH" ]; then
    log_info "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
  fi
fi

# Change to project root
cd "$RALPH_OLLAMA_DIR"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
  log_error "Python 3 is not installed or not in PATH"
  exit 1
fi

# Run the Python script with all arguments
log_info "Starting Ralph loop..."
python3 "$PYTHON_SCRIPT" "$@"
