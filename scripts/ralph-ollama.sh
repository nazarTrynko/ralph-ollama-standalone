#!/bin/bash

# Ralph Ollama Integration Script
# Runs Ralph workflow using Ollama as the LLM backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_OLLAMA_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$RALPH_OLLAMA_DIR/config"

# Default values
MODEL=""
CONFIG_FILE="$CONFIG_DIR/workflow-config.json"
OLLAMA_CONFIG="$CONFIG_DIR/ollama-config.json"
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --config)
      CONFIG_FILE="$2"
      shift 2
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --model MODEL     Use specific Ollama model (default: from config)"
      echo "  --config FILE     Use custom workflow config (default: config/workflow-config.json)"
      echo "  --verbose, -v     Enable verbose output"
      echo "  --help, -h        Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Functions
log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
  if [ "$VERBOSE" = true ]; then
    echo -e "[DEBUG] $1"
  fi
}

# Check if Ollama is installed
check_ollama() {
  if ! command -v ollama &> /dev/null; then
    log_error "Ollama is not installed. Please install from https://ollama.ai"
    exit 1
  fi
  log_debug "Ollama found: $(ollama --version 2>&1 || echo 'version unknown')"
}

# Check if Ollama server is running
check_ollama_server() {
  local host=$(jq -r '.server.host' "$OLLAMA_CONFIG" 2>/dev/null || echo "localhost")
  local port=$(jq -r '.server.port' "$OLLAMA_CONFIG" 2>/dev/null || echo "11434")
  
  if ! curl -s "http://$host:$port/api/tags" > /dev/null 2>&1; then
    log_error "Ollama server is not running on $host:$port"
    log_warn "Start Ollama server with: ollama serve"
    exit 1
  fi
  log_debug "Ollama server is running on $host:$port"
}

# Get default model from config
get_default_model() {
  if [ -z "$MODEL" ]; then
    MODEL=$(jq -r '.defaultModel' "$OLLAMA_CONFIG" 2>/dev/null || echo "llama3.2")
  fi
  log_debug "Using model: $MODEL"
}

# Check if model is available
check_model() {
  local host=$(jq -r '.server.host' "$OLLAMA_CONFIG" 2>/dev/null || echo "localhost")
  local port=$(jq -r '.server.port' "$OLLAMA_CONFIG" 2>/dev/null || echo "11434")
  
  local models=$(curl -s "http://$host:$port/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "")
  
  if echo "$models" | grep -q "^${MODEL}$"; then
    log_debug "Model $MODEL is available"
  else
    log_warn "Model $MODEL not found. Available models:"
    echo "$models" | sed 's/^/  - /'
    log_warn "Pull model with: ollama pull $MODEL"
    exit 1
  fi
}

# Load configuration
load_config() {
  if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Config file not found: $CONFIG_FILE"
    exit 1
  fi
  
  if [ ! -f "$OLLAMA_CONFIG" ]; then
    log_error "Ollama config file not found: $OLLAMA_CONFIG"
    exit 1
  fi
  
  log_debug "Loaded config from $CONFIG_FILE"
}

# Main execution
main() {
  log_info "Starting Ralph Ollama Integration"
  
  # Pre-flight checks
  check_ollama
  load_config
  check_ollama_server
  get_default_model
  check_model
  
  # Export environment variables for Ralph
  export RALPH_LLM_PROVIDER="ollama"
  export RALPH_LLM_MODEL="$MODEL"
  export RALPH_OLLAMA_CONFIG="$OLLAMA_CONFIG"
  export RALPH_WORKFLOW_CONFIG="$CONFIG_FILE"
  
  log_info "Configuration:"
  log_info "  Model: $MODEL"
  log_info "  Config: $CONFIG_FILE"
  log_info "  Ollama Config: $OLLAMA_CONFIG"
  
  log_info "Ralph workflow will use Ollama as LLM backend"
  log_warn "Note: This script sets environment variables."
  log_warn "Ralph workflow execution depends on your Ralph integration implementation."
  log_warn "Make sure your Ralph integration reads these environment variables."
  
  # If there's a Python script for Ralph, execute it
  if [ -f "$RALPH_OLLAMA_DIR/scripts/ralph-runner.py" ]; then
    log_info "Executing Ralph runner..."
    python3 "$RALPH_OLLAMA_DIR/scripts/ralph-runner.py" \
      --model "$MODEL" \
      --config "$CONFIG_FILE" \
      --ollama-config "$OLLAMA_CONFIG" \
      ${VERBOSE:+--verbose}
  else
    log_info "Ralph runner script not found. Environment variables set."
    log_info "Export these variables in your shell to use with Ralph:"
    echo "  export RALPH_LLM_PROVIDER=ollama"
    echo "  export RALPH_LLM_MODEL=$MODEL"
    echo "  export RALPH_OLLAMA_CONFIG=$OLLAMA_CONFIG"
    echo "  export RALPH_WORKFLOW_CONFIG=$CONFIG_FILE"
  fi
}

# Run main
main
