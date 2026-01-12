# Ralph Ollama - Standalone Project

> Complete Ralph Ollama integration - standalone version

This is a standalone copy of the Ralph Ollama integration, ready to use independently.

---

## Quick Start

```bash
# Setup virtual environment and install dependencies
./setup-venv.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Test the integration
python3 tests/test_connection.py

# Run examples
python3 examples/ralph_workflow_demo.py

# Or start the web UI to test interactively
python3 ui/app.py
# Then open http://localhost:5001 in your browser

# Or continuously improve your code
python3 scripts/improve-code.py --once --max-files 5

# Run end-to-end UI tests
python3 tests/test_ui_e2e.py

# Or use entry points (after pip install -e .)
ralph-ollama "Your prompt here"
ralph-ollama-ui  # Start web UI
```

---

## Project Structure

```
ralph-ollama-standalone/
├── README.md                 # This file
├── QUICK-START.md            # Quick start guide
├── USAGE.md                  # Usage patterns
├── config/                   # Configuration files
│   ├── ollama-config.json
│   └── workflow-config.json
├── lib/                      # Python library
│   ├── config.py
│   ├── ollama_client.py
│   └── __init__.py
├── integration/              # High-level adapter
│   ├── ralph_ollama_adapter.py
│   └── README.md
├── examples/                 # Example scripts
│   ├── simple_example.py
│   ├── ralph_workflow_demo.py
│   └── create_something.py
├── ui/                       # Web UI for testing
│   ├── app.py               # Flask server
│   ├── templates/           # HTML templates
│   └── README.md            # UI documentation
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
└── requirements.txt          # Python dependencies
```

---

## Usage

### Basic Usage

```python
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, 'lib')
sys.path.insert(0, 'integration')

from ralph_ollama_adapter import call_llm

# Use it
response = call_llm("Your prompt", task_type="implementation")
print(response)
```

### Environment Variables

```bash
export RALPH_LLM_PROVIDER=ollama
export RALPH_LLM_MODEL=llama3.2:latest
export RALPH_OLLAMA_CONFIG=./config/ollama-config.json
```

---

## Installation

### Option 1: Install as Package (Recommended)

```bash
# Install from source
pip install -e .

# Or install with UI dependencies
pip install -e ".[ui]"

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Option 2: Manual Setup

```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Requirements

- Python 3.8+
- Ollama server running (localhost:11434)
- At least one model pulled (e.g., `ollama pull llama3.2`)
- `requests` module (install via `pip install -r requirements.txt`)

---

## Documentation

- **Quick Start:** [QUICK-START.md](QUICK-START.md)
- **Installation:** [docs/INSTALLATION.md](docs/INSTALLATION.md) - Detailed installation guide
- **Usage Guide:** [USAGE.md](USAGE.md)
- **API Reference:** [docs/API.md](docs/API.md)
- **Setup:** [docs/SETUP.md](docs/SETUP.md)
- **Integration:** [docs/INTEGRATION.md](docs/INTEGRATION.md)
- **Troubleshooting:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Code Improvement:** [docs/CODE-IMPROVEMENT.md](docs/CODE-IMPROVEMENT.md) - Automated code improvement

---

## Status

✅ Complete and ready to use  
✅ Enhanced with validation, error handling, logging, and tests  
✅ Standalone - no dependencies on parent project  
✅ Installable via pip: `pip install -e .`

---

**Version:** 1.1.0  
**Source:** Copied from `.cursor/ralph-ollama/` in self-app project  
**Last Updated:** 2025-01-12

**Recent Improvements:** See [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) for details on v1.1.0 enhancements.
