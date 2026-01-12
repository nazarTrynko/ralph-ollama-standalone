# Examples

Example scripts demonstrating how to use the Ollama integration with Ralph workflow.

---

## Simple Example

**File:** `simple_example.py`

Demonstrates basic usage of the OllamaClient:

```bash
python3 examples/simple_example.py
```

Shows:

- Basic prompt generation
- System prompts
- Convenience functions
- Model listing
- Ralph workflow style usage

---

## Test Connection

**File:** `../tests/test_connection.py`

Test script to verify Ollama setup:

```bash
python3 tests/test_connection.py
```

Tests:

- Configuration loading
- Server connection
- Model listing
- Model generation

---

## Usage in Your Code

### Basic Usage

```python
from pathlib import Path
import sys

# Add lib to path
lib_path = Path(__file__).parent.parent / 'lib'
sys.path.insert(0, str(lib_path))

from ollama_client import OllamaClient

# Initialize
client = OllamaClient()

# Generate response
result = client.generate(
    prompt="Write a Python function to reverse a string.",
    model="codellama"
)

print(result['response'])
```

### Using Convenience Function

```python
from ollama_client import get_llm_response

response = get_llm_response(
    prompt="Explain this code: def foo(x): return x * 2",
    model="codellama"
)

print(response)
```

### With Environment Variables

```bash
export RALPH_LLM_PROVIDER=ollama
export RALPH_LLM_MODEL=codellama
export RALPH_OLLAMA_CONFIG=./config/ollama-config.json

python3 your_script.py
```

---

## Integration with Ralph Workflow

See `../docs/INTEGRATION.md` for detailed integration patterns.

---

**Last Updated:** 2024
