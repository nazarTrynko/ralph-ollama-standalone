# Standalone Project Setup

**Project:** Ralph Ollama Standalone  
**Location:** `/Users/nazartrynko/ralph-ollama-standalone/`  
**Status:** ✅ Complete and ready to use

---

## What This Is

A complete, standalone copy of the Ralph Ollama integration. This project is **fully independent** and can be used anywhere, moved anywhere, or shared with others.

---

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/nazartrynko/ralph-ollama-standalone

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Ollama is Running

```bash
# Check if Ollama server is accessible
curl http://localhost:11434/api/tags

# If not running, start it:
ollama serve
```

### 3. Test the Integration

```bash
# Run connection test
python3 tests/test_connection.py

# Run simple example
python3 examples/simple_example.py
```

---

## Project Structure

```
ralph-ollama-standalone/
├── README.md                 # Main documentation
├── QUICK-START.md            # Quick start guide
├── USAGE.md                  # Usage patterns
├── config/                   # Configuration files
│   ├── ollama-config.json
│   └── workflow-config.json
├── lib/                      # Python library
│   ├── config.py            # Configuration utilities
│   ├── ollama_client.py     # Ollama API client
│   └── __init__.py
├── integration/              # High-level adapter
│   ├── ralph_ollama_adapter.py
│   └── README.md
├── examples/                 # Example scripts
│   ├── simple_example.py
│   ├── ralph_workflow_demo.py
│   └── create_something.py
├── scripts/                  # Shell scripts
│   ├── setup-ollama.sh
│   ├── model-manager.sh
│   └── ralph-ollama.sh
├── tests/                     # Test utilities
│   └── test_connection.py
├── docs/                      # Documentation
│   ├── SETUP.md
│   ├── MODEL-GUIDE.md
│   ├── INTEGRATION.md
│   └── TROUBLESHOOTING.md
├── templates/                 # Templates
│   └── system-prompts/
└── requirements.txt          # Python dependencies
```

---

## Key Differences from Original

### Path Updates

All paths have been updated to be relative to the project root:

- **Before:** `.cursor/ralph-ollama/config/ollama-config.json`
- **After:** `config/ollama-config.json`

### Self-Contained

- No dependencies on `.cursor/` structure
- No dependencies on `self-app` project
- Can be moved anywhere
- All imports use relative paths

---

## Usage Examples

### Basic Usage

```python
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, 'lib')
sys.path.insert(0, 'integration')

from ralph_ollama_adapter import call_llm

# Use it
response = call_llm("Write a Python function to reverse a string")
print(response)
```

### With Task Types

```python
from ralph_ollama_adapter import call_llm

# Implementation task (uses codellama)
code = call_llm(
    "Write a function to calculate factorial",
    task_type="implementation"
)

# Documentation task (uses llama3.2)
docs = call_llm(
    "Document this API endpoint",
    task_type="documentation"
)
```

### Environment Variables

```bash
export RALPH_LLM_PROVIDER=ollama
export RALPH_LLM_MODEL=llama3.2:latest
export RALPH_OLLAMA_CONFIG=./config/ollama-config.json

# Then use in your scripts
python3 your_script.py
```

---

## Requirements

- **Python 3.8+**
- **Ollama server** running (localhost:11434)
- **At least one model** pulled (e.g., `ollama pull llama3.2`)
- **requests module** (install via `pip install -r requirements.txt`)

---

## Documentation

All documentation is included:

- **Quick Start:** [QUICK-START.md](QUICK-START.md)
- **Usage Guide:** [USAGE.md](USAGE.md)
- **Setup:** [docs/SETUP.md](docs/SETUP.md)
- **Integration:** [docs/INTEGRATION.md](docs/INTEGRATION.md)
- **Troubleshooting:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Model Guide:** [docs/MODEL-GUIDE.md](docs/MODEL-GUIDE.md)

---

## Next Steps

1. ✅ **Files copied** - All files are in place
2. ⏭️ **Install dependencies** - Run `pip install -r requirements.txt`
3. ⏭️ **Verify Ollama** - Make sure Ollama server is running
4. ⏭️ **Run tests** - Execute `python3 tests/test_connection.py`
5. ⏭️ **Try examples** - Run example scripts to see it in action

---

## Support

- See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
- Check [INTEGRATION.md](docs/INTEGRATION.md) for integration patterns
- Review [MODEL-GUIDE.md](docs/MODEL-GUIDE.md) for model selection

---

**Status:** ✅ Ready to use!  
**Version:** 1.0.0  
**Source:** Copied from `.cursor/ralph-ollama/` in self-app project
