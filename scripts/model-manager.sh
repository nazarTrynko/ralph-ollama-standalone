#!/bin/bash

# Ollama Model Management Script
# Utilities for managing Ollama models

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_HOST="${OLLAMA_HOST:-localhost:11434}"

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check Ollama server
check_server() {
  if ! curl -s "http://${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
    log_error "Ollama server is not running on $OLLAMA_HOST"
    log_warn "Start with: ollama serve"
    exit 1
  fi
}

# List models
list_models() {
  check_server
  
  log_info "Available models:"
  echo ""
  
  local models=$(curl -s "http://${OLLAMA_HOST}/api/tags" | jq -r '.models[] | "\(.name)\t\(.size // 0 | . / 1024 / 1024 / 1024 | floor)GB"' 2>/dev/null || echo "")
  
  if [ -z "$models" ]; then
    log_warn "No models found"
    return 1
  fi
  
  echo "$models" | while IFS=$'\t' read -r name size; do
    echo -e "  ${BLUE}${name}${NC}\t${size}GB"
  done
}

# Pull model
pull_model() {
  local model=$1
  
  if [ -z "$model" ]; then
    log_error "Model name required"
    echo "Usage: $0 pull <model-name>"
    exit 1
  fi
  
  log_info "Pulling model: $model"
  ollama pull "$model"
}

# Remove model
remove_model() {
  local model=$1
  
  if [ -z "$model" ]; then
    log_error "Model name required"
    echo "Usage: $0 remove <model-name>"
    exit 1
  fi
  
  log_warn "Removing model: $model"
  read -p "Are you sure? (y/N): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    ollama rm "$model"
    log_info "Model removed: $model"
  else
    log_info "Cancelled"
  fi
}

# Show model info
show_model() {
  local model=$1
  
  if [ -z "$model" ]; then
    log_error "Model name required"
    echo "Usage: $0 info <model-name>"
    exit 1
  fi
  
  check_server
  
  log_info "Model info: $model"
  echo ""
  
  # Try to get model details
  local response=$(curl -s "http://${OLLAMA_HOST}/api/show" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$model\"}" 2>/dev/null)
  
  if echo "$response" | jq -e '.' > /dev/null 2>&1; then
    echo "$response" | jq '.'
  else
    log_warn "Could not fetch model details"
  fi
}

# Test model
test_model() {
  local model=$1
  
  if [ -z "$model" ]; then
    log_error "Model name required"
    echo "Usage: $0 test <model-name>"
    exit 1
  fi
  
  check_server
  
  log_info "Testing model: $model"
  
  local response=$(curl -s -X POST "http://${OLLAMA_HOST}/api/generate" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"$model\",
      \"prompt\": \"Say hello in one word.\",
      \"stream\": false
    }" 2>/dev/null)
  
  if echo "$response" | jq -e '.response' > /dev/null 2>&1; then
    local output=$(echo "$response" | jq -r '.response')
    log_info "✓ Model is working"
    echo "Response: $output"
    return 0
  else
    log_error "✗ Model test failed"
    return 1
  fi
}

# Show help
show_help() {
  echo "Ollama Model Manager"
  echo ""
  echo "Usage: $0 <command> [arguments]"
  echo ""
  echo "Commands:"
  echo "  list                    List all available models"
  echo "  pull <model>            Pull/download a model"
  echo "  remove <model>          Remove a model"
  echo "  info <model>            Show model information"
  echo "  test <model>            Test a model with a simple prompt"
  echo "  help                    Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 list"
  echo "  $0 pull llama3.2"
  echo "  $0 test llama3.2"
  echo "  $0 remove old-model"
}

# Main
main() {
  case "${1:-help}" in
    list)
      list_models
      ;;
    pull)
      pull_model "$2"
      ;;
    remove|rm)
      remove_model "$2"
      ;;
    info)
      show_model "$2"
      ;;
    test)
      test_model "$2"
      ;;
    help|--help|-h)
      show_help
      ;;
    *)
      log_error "Unknown command: $1"
      echo ""
      show_help
      exit 1
      ;;
  esac
}

main "$@"
