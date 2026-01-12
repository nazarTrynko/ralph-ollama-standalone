#!/bin/bash
# Setup Ollama for CI/CD environment
# Installs Ollama and pulls a test model

set -e

echo "🚀 Setting up Ollama for CI/CD..."

# Install Ollama
echo "📦 Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server in background
echo "🔄 Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for server to start
echo "⏳ Waiting for Ollama server to start..."
sleep 5

# Verify server is running
for i in {1..10}; do
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama server is running"
    break
  fi
  if [ $i -eq 10 ]; then
    echo "❌ Failed to start Ollama server"
    exit 1
  fi
  echo "  Attempt $i/10: Waiting..."
  sleep 2
done

# Determine which model to pull
MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
echo "📥 Pulling model: $MODEL"

# Pull model with timeout
if timeout 300 ollama pull "$MODEL"; then
  echo "✅ Model $MODEL pulled successfully"
else
  echo "⚠️  Failed to pull $MODEL, trying fallback..."
  # Try a smaller fallback model
  FALLBACK_MODEL="phi3:mini"
  if timeout 180 ollama pull "$FALLBACK_MODEL"; then
    echo "✅ Fallback model $FALLBACK_MODEL pulled successfully"
    export OLLAMA_MODEL="$FALLBACK_MODEL"
  else
    echo "❌ Failed to pull any model"
    echo "⚠️  E2E tests may fail without a model"
  fi
fi

# List available models
echo "📋 Available models:"
ollama list || echo "No models available"

echo "✅ Ollama setup complete"
