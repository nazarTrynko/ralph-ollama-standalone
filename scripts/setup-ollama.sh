#!/bin/bash

# Ollama Setup and Validation Script
# Checks Ollama installation and sets up initial configuration

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RALPH_OLLAMA_DIR="$(dirname "$SCRIPT_DIR")"

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check Ollama installation
check_ollama_installed() {
  log_info "Checking Ollama installation..."
  
  if command -v ollama &> /dev/null; then
    local version=$(ollama --version 2>&1 || echo "unknown")
    log_info "✓ Ollama is installed: $version"
    return 0
  else
    log_error "✗ Ollama is not installed"
    log_warn "Install from: https://ollama.ai"
    log_warn "  macOS: brew install ollama"
    log_warn "  Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    return 1
  fi
}

# Check Ollama server
check_ollama_server() {
  log_info "Checking Ollama server..."
  
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    log_info "✓ Ollama server is running"
    return 0
  else
    log_warn "✗ Ollama server is not running"
    log_warn "Start with: ollama serve"
    return 1
  fi
}

# List available models
list_models() {
  log_info "Checking available models..."
  
  local models=$(curl -s http://localhost:11434/api/tags 2>/dev/null | jq -r '.models[].name' 2>/dev/null || echo "")
  
  if [ -z "$models" ]; then
    log_warn "No models found. Pull a model with: ollama pull llama3.2"
    return 1
  else
    log_info "Available models:"
    echo "$models" | sed 's/^/  - /'
    return 0
  fi
}

# Check for recommended models
check_recommended_models() {
  log_info "Checking recommended models..."
  
  local recommended=("llama3.2" "codellama")
  local models=$(curl -s http://localhost:11434/api/tags 2>/dev/null | jq -r '.models[].name' 2>/dev/null || echo "")
  
  local missing=()
  for model in "${recommended[@]}"; do
    if ! echo "$models" | grep -q "^${model}$"; then
      missing+=("$model")
    fi
  done
  
  if [ ${#missing[@]} -eq 0 ]; then
    log_info "✓ All recommended models are available"
    return 0
  else
    log_warn "Recommended models not found:"
    for model in "${missing[@]}"; do
      echo "  - $model (install with: ollama pull $model)"
    done
    return 1
  fi
}

# Test model connection
test_model() {
  local model=${1:-"llama3.2"}
  
  log_info "Testing model: $model"
  
  local response=$(curl -s -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"$model\",
      \"prompt\": \"Hello\",
      \"stream\": false
    }" 2>/dev/null)
  
  if echo "$response" | jq -e '.response' > /dev/null 2>&1; then
    log_info "✓ Model $model is working"
    return 0
  else
    log_error "✗ Model $model test failed"
    return 1
  fi
}

# Main
main() {
  log_info "Ollama Setup and Validation"
  echo ""
  
  local all_checks_passed=true
  
  check_ollama_installed || all_checks_passed=false
  echo ""
  
  if check_ollama_server; then
    list_models
    echo ""
    check_recommended_models
    echo ""
    test_model "llama3.2" || all_checks_passed=false
  else
    all_checks_passed=false
  fi
  
  echo ""
  if [ "$all_checks_passed" = true ]; then
    log_info "✓ Setup validation complete - Ollama is ready!"
  else
    log_warn "Some checks failed. Please address the issues above."
    exit 1
  fi
}

main
