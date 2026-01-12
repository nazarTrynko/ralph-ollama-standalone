# Quick Start Guide

Get up and running with Ralph Ollama in 5 minutes.

---

## 1. Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh
```

---

## 2. Start Ollama & Pull Model

```bash
# Start server (keep running)
ollama serve

# In another terminal, pull a model
ollama pull llama3.2
```

---

## 3. Verify Setup

```bash
cd .cursor/ralph-ollama
chmod +x scripts/*.sh

# Quick validation (checks structure)
bash run_tests.sh

# Full setup validation (requires Ollama running)
./scripts/setup-ollama.sh
```

---

## 4. Run Ralph with Ollama

```bash
# Option 1: Use the script
./scripts/ralph-ollama.sh --model llama3.2

# Option 2: Use Python library
pip install -r requirements.txt  # First time only
python3 -m lib.ollama_client "Your prompt here"

# Option 3: Use adapter (for integration)
export RALPH_LLM_PROVIDER=ollama
python3 integration/ralph_ollama_adapter.py "Your prompt" implementation

# Option 4: Set environment variables and run your workflow
export RALPH_LLM_PROVIDER=ollama
export RALPH_LLM_MODEL=llama3.2
export RALPH_OLLAMA_CONFIG=.cursor/ralph-ollama/config/ollama-config.json
# Then run your Ralph workflow
```

---

## What's Next?

- 📖 **Full Setup**: See `docs/SETUP.md`
- 🎯 **Model Selection**: See `docs/MODEL-GUIDE.md`
- 🔧 **Integration**: See `docs/INTEGRATION.md`
- 🐛 **Troubleshooting**: See `docs/TROUBLESHOOTING.md`

---

**That's it!** You're ready to run Ralph workflows with local LLM.
