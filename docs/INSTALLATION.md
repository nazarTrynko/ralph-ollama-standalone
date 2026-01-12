# Installation Guide

Complete guide for installing and setting up Ralph Ollama integration.

---

## Prerequisites

- **Python 3.8+** - Required for the integration
- **Ollama** - Local LLM server (install from https://ollama.ai)
- **pip** - Python package manager (usually comes with Python)

---

## Installation Methods

### Method 1: Install as Package (Recommended)

This method installs the package in editable mode, allowing you to use it from anywhere and make changes easily.

#### Basic Installation

```bash
# Clone or navigate to the project directory
cd ralph-ollama-standalone

# Install the package
pip install -e .
```

This installs:
- Core library (`lib` package)
- Integration adapter (`integration` package)
- Command-line tools (`ralph-ollama`)

#### With UI Dependencies

To use the web UI, install with UI extras:

```bash
pip install -e ".[ui]"
```

This adds:
- Flask web framework
- Flask-CORS for cross-origin requests
- Web UI server (`ralph-ollama-ui` command)

#### With Development Dependencies

For development and testing:

```bash
pip install -e ".[dev]"
```

This adds:
- pytest and pytest-mock for testing
- mypy for type checking
- black for code formatting
- flake8 for linting

#### Verify Installation

After installation, verify it works:

```bash
# Test package imports
python3 -c "from lib.ollama_client import OllamaClient; print('✅ Package installed correctly')"

# Test entry point
ralph-ollama --help

# Test UI entry point (if UI installed)
ralph-ollama-ui --help
```

---

### Method 2: Manual Setup with Virtual Environment

For isolated installation without package installation:

#### Step 1: Create Virtual Environment

```bash
# Navigate to project
cd ralph-ollama-standalone

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows
```

#### Step 2: Install Dependencies

```bash
# Install base dependencies
pip install -r requirements.txt

# Or install with UI dependencies
pip install -r requirements.txt flask flask-cors
```

#### Step 3: Verify Installation

```bash
# Test imports
python3 -c "import sys; sys.path.insert(0, '.'); from lib.ollama_client import OllamaClient; print('✅ Setup complete')"
```

---

## Post-Installation Setup

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

### 2. Start Ollama Server

```bash
# Start Ollama server (keep running)
ollama serve
```

### 3. Pull Models

```bash
# Pull recommended models
ollama pull llama3.2
ollama pull codellama

# Or pull others
ollama pull mistral
ollama pull phi3
```

### 4. Verify Setup

```bash
# Test connection
python3 tests/test_connection.py

# Or use the test script
bash run_tests.sh
```

---

## Using Entry Points

After package installation, you can use command-line tools:

### ralph-ollama

Direct Ollama client from command line:

```bash
# Basic usage
ralph-ollama "Write a Python function to calculate factorial"

# With specific model
ralph-ollama "Explain recursion" llama3.2
```

### ralph-ollama-ui

Start the web UI server:

```bash
# Start UI server (default port 5001)
ralph-ollama-ui

# Or with custom port
FLASK_PORT=8080 ralph-ollama-ui
```

Then open http://localhost:5001 in your browser.

---

## Troubleshooting Installation

### "No module named 'lib'" Error

**Solution:** Make sure you're in the project directory and have installed the package:
```bash
pip install -e .
```

### "No module named 'requests'" Error

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### "No module named 'flask'" Error (UI)

**Solution:** Install UI dependencies:
```bash
pip install -e ".[ui]"
# OR
pip install flask flask-cors
```

### Entry Points Not Found

**Solution:** Reinstall the package:
```bash
pip install -e . --force-reinstall
```

### Port 5000 Already in Use

**Solution:** The UI now defaults to port 5001. To use a different port:
```bash
FLASK_PORT=8080 ralph-ollama-ui
```

### Virtual Environment Issues

**Solution:** Make sure virtual environment is activated:
```bash
# Check if activated (should show (venv) in prompt)
which python  # Should point to venv/bin/python

# If not activated
source venv/bin/activate
```

---

## Development Installation

For contributing or development:

```bash
# Install with all dependencies
pip install -e ".[dev,ui]"

# Run tests
pytest tests/ -v

# Run linting
black --check lib/ integration/ ui/
flake8 lib/ integration/ ui/
mypy lib/ integration/ ui/
```

---

## Uninstallation

To uninstall the package:

```bash
pip uninstall ralph-ollama
```

This removes the package but keeps your project files intact.

---

## Next Steps

After installation:

1. **Read the Quick Start**: [QUICK-START.md](../QUICK-START.md)
2. **Try the Examples**: [examples/](../examples/)
3. **Start the UI**: `ralph-ollama-ui` or `python3 ui/app.py`
4. **Read the API Docs**: [docs/API.md](API.md)
5. **Check Usage Guide**: [USAGE.md](../USAGE.md)

---

**Last Updated:** 2025-01-12
