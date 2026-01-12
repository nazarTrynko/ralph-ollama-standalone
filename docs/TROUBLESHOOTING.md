# Troubleshooting Guide

Common issues and solutions for Ralph Ollama integration.

---

## Connection Issues

### Ollama Server Not Running

**Symptoms:**
- `Connection refused` errors
- `curl: (7) Failed to connect to localhost port 11434`

**Solution:**
```bash
# Start Ollama server
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

**Prevention:**
- Install Ollama as a service (starts automatically)
- Add to startup scripts
- Use process managers (systemd, launchd)

---

### Wrong Port/Host

**Symptoms:**
- Connection errors
- Cannot reach Ollama API

**Solution:**
1. Check Ollama is running on expected port:
```bash
# Default port is 11434
netstat -an | grep 11434
```

2. Update config if using custom port:
```json
// config/ollama-config.json
{
  "server": {
    "host": "localhost",
    "port": 11434  // Change if needed
  }
}
```

3. Set environment variable:
```bash
export OLLAMA_HOST=localhost:11434
```

---

## Model Issues

### Model Not Found

**Symptoms:**
- `Error: model 'xxx' not found`
- Model list doesn't show expected model

**Solution:**
```bash
# List available models
ollama list

# Pull the model
ollama pull llama3.2

# Verify
./scripts/model-manager.sh list
```

**Check:**
- Model name spelling (case-sensitive)
- Model is actually pulled
- Ollama server has access to models

---

### Model Loading Fails

**Symptoms:**
- Model loads but then fails
- Out of memory errors
- Segmentation faults

**Possible Causes:**

1. **Insufficient Memory**
```bash
# Check available memory
free -h  # Linux
vm_stat  # macOS

# Solution: Use smaller model or free memory
ollama pull phi3  # Smaller model
```

2. **Corrupted Model**
```bash
# Remove and re-pull
ollama rm llama3.2
ollama pull llama3.2
```

3. **Disk Space**
```bash
# Check disk space
df -h

# Clean up if needed
ollama rm <unused-model>
```

---

### Slow Model Responses

**Symptoms:**
- Very slow generation (>30 seconds)
- High CPU usage
- System becomes unresponsive

**Solutions:**

1. **Use Smaller Model**
```bash
# Switch to faster model
./scripts/ralph-ollama.sh --model phi3
```

2. **Reduce Token Count**
```json
// config/ollama-config.json
{
  "models": {
    "llama3.2": {
      "parameters": {
        "numPredict": 2048  // Reduce from 4096
      }
    }
  }
}
```

3. **Lower Temperature**
```json
{
  "parameters": {
    "temperature": 0.3  // More deterministic, faster
  }
}
```

4. **Check System Resources**
```bash
# Monitor CPU/RAM
top
htop  # If available
```

5. **Enable GPU (if available)**
- Check GPU support: `ollama show llama3.2`
- Ensure GPU drivers installed
- Ollama should auto-detect GPU

---

## Configuration Issues

### Config File Not Found

**Symptoms:**
- Script errors about missing config
- Default values not working

**Solution:**
```bash
# Check config files exist
ls -la config/

# Verify paths in scripts
./scripts/ralph-ollama.sh --config config/workflow-config.json
```

---

### Invalid JSON in Config

**Symptoms:**
- `jq` errors
- Script fails to parse config

**Solution:**
```bash
# Validate JSON
jq . config/ollama-config.json

# Fix syntax errors
# Common issues:
# - Missing commas
# - Trailing commas
# - Unmatched quotes
```

---

## Script Issues

### Permission Denied

**Symptoms:**
- `Permission denied` when running scripts
- Scripts not executable

**Solution:**
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Verify
ls -l scripts/
```

---

### Script Not Found

**Symptoms:**
- `No such file or directory`
- Script path errors

**Solution:**
```bash
# Run from project root directory
./scripts/ralph-ollama.sh

# Or use absolute path
/path/to/ralph-ollama-standalone/scripts/ralph-ollama.sh
```

---

### jq Not Installed

**Symptoms:**
- `jq: command not found`
- JSON parsing fails

**Solution:**
```bash
# macOS
brew install jq

# Linux (Debian/Ubuntu)
sudo apt-get install jq

# Linux (RHEL/CentOS)
sudo yum install jq

# Verify
jq --version
```

---

## Workflow Integration Issues

### Environment Variables Not Set

**Symptoms:**
- Ralph doesn't use Ollama
- Falls back to cloud API

**Solution:**
```bash
# Set environment variables
export RALPH_LLM_PROVIDER=ollama
export RALPH_LLM_MODEL=llama3.2
export RALPH_OLLAMA_CONFIG=./config/ollama-config.json

# Verify
echo $RALPH_LLM_PROVIDER
```

**Or use the script:**
```bash
./scripts/ralph-ollama.sh
```

---

### Ralph Doesn't Recognize Ollama

**Symptoms:**
- Ralph workflow ignores Ollama config
- Uses default provider

**Possible Causes:**

1. **Ralph integration not implemented**
   - Check if Ralph code reads `RALPH_LLM_PROVIDER`
   - May need to implement Ollama integration

2. **Config path incorrect**
   - Verify `RALPH_OLLAMA_CONFIG` path
   - Check file exists and is readable

3. **Provider name mismatch**
   - Should be `ollama` (lowercase)
   - Check Ralph code for expected provider name

---

## Performance Issues

### High Memory Usage

**Symptoms:**
- System runs out of memory
- Swapping to disk
- Slow performance

**Solutions:**

1. **Use Smaller Models**
```bash
ollama pull phi3  # 2.3GB vs 3.8GB for codellama
```

2. **Close Other Applications**
- Free up RAM
- Close browser tabs
- Stop other services

3. **Reduce Context Window**
```json
{
  "models": {
    "llama3.2": {
      "parameters": {
        "numPredict": 2048  // Reduce context
      }
    }
  }
}
```

4. **Use Quantized Models** (if available)
- Smaller file sizes
- Lower memory usage
- Slightly lower quality

---

### Slow First Response

**Symptoms:**
- First request is very slow
- Subsequent requests faster

**Explanation:**
- Model loading into memory takes time
- Normal behavior
- First request: 10-30 seconds
- Subsequent: 2-8 seconds

**Solution:**
- Keep Ollama server running
- Pre-warm model with test request
- Acceptable for development workflow

---

## Quality Issues

### Poor Code Quality

**Symptoms:**
- Generated code has errors
- Doesn't follow patterns
- Low quality output

**Solutions:**

1. **Use Better Model**
```bash
# Switch to codellama for code tasks
./scripts/ralph-ollama.sh --model codellama
```

2. **Improve Prompts**
- Use system prompts from `templates/system-prompts/`
- Be more explicit in instructions
- Provide examples

3. **Adjust Parameters**
```json
{
  "parameters": {
    "temperature": 0.3,  // Lower = more deterministic
    "topP": 0.95,
    "repeatPenalty": 1.1
  }
}
```

4. **Break Down Tasks**
- Smaller, focused tasks work better
- One function at a time
- Clear, specific instructions

---

### Inconsistent Responses

**Symptoms:**
- Same prompt gives different results
- Unpredictable outputs

**Solutions:**

1. **Lower Temperature**
```json
{
  "parameters": {
    "temperature": 0.3  // More deterministic
  }
}
```

2. **Use Seed** (if supported)
- Makes outputs reproducible
- Check Ollama docs for seed parameter

3. **Clearer Prompts**
- More explicit instructions
- Less ambiguity
- Provide structure

---

## Getting Help

### Diagnostic Information

Collect this information when reporting issues:

```bash
# System info
uname -a
ollama --version
jq --version

# Ollama status
curl http://localhost:11434/api/tags
ollama list

# Model test
./scripts/model-manager.sh test llama3.2

# Config check
cat config/ollama-config.json | jq .
cat config/workflow-config.json | jq .
```

### Logs

Check for error messages:
- Script output (verbose mode: `--verbose`)
- Ollama server logs
- System logs (if available)

### Resources

- Ollama Documentation: https://ollama.ai/docs
- Ollama GitHub: https://github.com/ollama/ollama
- Model Documentation: Check model-specific docs

---

**Last Updated:** 2024
