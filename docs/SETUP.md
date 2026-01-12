# Setup Guide: Ralph Ollama Integration

Complete guide for setting up Ralph workflows with Ollama (local LLM).

---

## Prerequisites

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download

### 2. Install Dependencies

**Required:**
- `curl` - For API requests
- `jq` - For JSON parsing
  - macOS: `brew install jq`
  - Linux: `sudo apt-get install jq` or `sudo yum install jq`

**Optional:**
- `python3` - If using Python integration scripts
- `bash` 4.0+ - For script execution

---

## Installation Steps

### Step 1: Start Ollama Server

```bash
# Start Ollama server (runs on port 11434)
ollama serve
```

Keep this running in a terminal. The server will start automatically on system boot if installed as a service.

### Step 2: Pull Models

Pull the models you want to use:

```bash
# Recommended: General purpose model
ollama pull llama3.2

# Recommended: Code-focused model
ollama pull codellama

# Optional: Other useful models
ollama pull mistral      # Good for reasoning
ollama pull phi3         # Lightweight, fast
```

**Model Sizes:**
- llama3.2: ~2GB
- codellama: ~3.8GB
- mistral: ~4.1GB
- phi3: ~2.3GB

### Step 3: Verify Installation

Run the setup validation script:

```bash
cd .cursor/ralph-ollama
chmod +x scripts/*.sh
./scripts/setup-ollama.sh
```

This will check:
- ✅ Ollama installation
- ✅ Server running
- ✅ Models available
- ✅ Model connectivity

### Step 4: Configure (Optional)

Edit configuration files if needed:

```bash
# Ollama connection settings
nano config/ollama-config.json

# Workflow settings
nano config/workflow-config.json
```

**Default Configuration:**
- Server: `localhost:11434`
- Default Model: `llama3.2`
- Timeout: 300 seconds

### Step 5: Test Connection

Test a specific model:

```bash
./scripts/model-manager.sh test llama3.2
```

Expected output:
```
[INFO] Testing model: llama3.2
[INFO] ✓ Model is working
Response: Hello
```

---

## Integration with Ralph Workflow

### Method 1: Environment Variables

Set environment variables and run Ralph:

```bash
export RALPH_LLM_PROVIDER=ollama
export RALPH_LLM_MODEL=llama3.2
export RALPH_OLLAMA_CONFIG=.cursor/ralph-ollama/config/ollama-config.json

# Run your Ralph workflow
# (depends on your Ralph implementation)
```

### Method 2: Using the Script

Use the provided script:

```bash
./scripts/ralph-ollama.sh --model llama3.2
```

This sets up environment variables automatically.

### Method 3: Direct Integration

If you have a custom Ralph integration, modify it to:

1. Read `RALPH_OLLAMA_CONFIG` environment variable
2. Load Ollama configuration
3. Route LLM calls to Ollama API instead of cloud APIs

---

## Model Selection Guide

### For Implementation Tasks
- **Preferred:** `codellama`
- **Fallback:** `llama3.2`
- **Why:** Better code generation, larger context window

### For Documentation Tasks
- **Preferred:** `llama3.2`
- **Fallback:** `phi3`
- **Why:** Good language understanding, faster

### For Code Review
- **Preferred:** `codellama`
- **Fallback:** `llama3.2`
- **Why:** Understands code patterns, syntax

### For Architecture/Planning
- **Preferred:** `mistral`
- **Fallback:** `llama3.2`
- **Why:** Better reasoning capabilities

### For Quick Fixes
- **Preferred:** `phi3`
- **Fallback:** `llama3.2`
- **Why:** Fast response times

---

## Troubleshooting

### Ollama Server Not Running

**Symptom:** Connection refused errors

**Solution:**
```bash
# Start Ollama server
ollama serve

# Or check if it's running
curl http://localhost:11434/api/tags
```

### Model Not Found

**Symptom:** Model not found errors

**Solution:**
```bash
# List available models
ollama list

# Pull the model
ollama pull <model-name>

# Verify
./scripts/model-manager.sh list
```

### Out of Memory

**Symptom:** Model loading fails, system runs out of memory

**Solution:**
- Use smaller models (phi3, llama3.2-small)
- Close other applications
- Reduce model context window in config
- Use quantized models if available

### Slow Responses

**Symptom:** Very slow response times

**Solution:**
- Use smaller/faster models (phi3)
- Reduce `numPredict` parameter
- Check system resources (CPU, RAM)
- Consider GPU acceleration (if available)

### Connection Timeout

**Symptom:** Request timeouts

**Solution:**
- Increase timeout in `config/ollama-config.json`
- Check server is running
- Verify network connectivity
- Check firewall settings

---

## Performance Optimization

### For Faster Responses

1. Use smaller models (phi3, llama3.2)
2. Reduce `numPredict` (max tokens) in config
3. Lower temperature for more deterministic outputs
4. Enable response caching (if available)

### For Better Quality

1. Use larger models (codellama, mistral)
2. Increase context window
3. Use model-specific prompts
4. Increase `numPredict` for longer outputs

### Hardware Recommendations

**Minimum:**
- 8GB RAM
- 4 CPU cores
- 10GB free disk space

**Recommended:**
- 16GB+ RAM
- 8+ CPU cores
- GPU with 8GB+ VRAM (optional but recommended)
- SSD storage

---

## Next Steps

1. ✅ Complete setup validation
2. ✅ Test model connections
3. ✅ Configure workflow settings
4. ✅ Integrate with Ralph workflow
5. ✅ Run your first task

See `MODEL-GUIDE.md` for detailed model comparisons and `TROUBLESHOOTING.md` for common issues.

---

**Last Updated:** 2024
