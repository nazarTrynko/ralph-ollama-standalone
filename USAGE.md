# Usage Guide

Quick reference for using Ralph Ollama integration.

---

## Quick Start

### 1. Setup (One-time)

```bash
# Activate virtual environment
source venv/bin/activate

# (Dependencies should already be installed)
# If needed: pip install -r requirements.txt
```

### 2. Verify Ollama is Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Or use the test script
python3 tests/test_connection.py
```

### 3. Use It!

---

## Usage Patterns

### Pattern 1: Simple Function Call

```python
import sys
from pathlib import Path

from lib.path_utils import setup_paths
setup_paths()

from ralph_ollama_adapter import call_llm

# Use it
response = call_llm("Write a Python function to reverse a string")
print(response)
```

### Pattern 2: Task-Based Generation

```python
from ralph_ollama_adapter import call_llm

# Implementation task (uses codellama)
code = call_llm(
    "Write a function to calculate fibonacci",
    task_type="implementation"
)

# Documentation task (uses llama3.2)
docs = call_llm(
    "Document this API endpoint",
    task_type="documentation"
)

# Testing task (uses llama3.2)
tests = call_llm(
    "Write unit tests for this function",
    task_type="testing"
)
```

### Pattern 3: Using the Adapter Directly

```python
from ralph_ollama_adapter import RalphOllamaAdapter

adapter = RalphOllamaAdapter()

# Check if available
if adapter.check_available():
    result = adapter.generate(
        prompt="Review this code for bugs",
        task_type="code-review"
    )
    print(result['content'])
```

### Pattern 4: Low-Level Client

```python
from lib.ollama_client import OllamaClient

client = OllamaClient()
result = client.generate(
    prompt="Your prompt here",
    model="llama3.2:latest"
)
print(result['response'])
```

---

## Running the Demo

```bash
source venv/bin/activate
python3 examples/ralph_workflow_demo.py
```

This demonstrates:

- Basic Ollama usage
- Ralph workflow patterns
- Task-based model selection
- Complete workflow example

---

## Common Use Cases

### Use Case 1: Code Generation

```python
from ralph_ollama_adapter import call_llm

code = call_llm(
    """
    Write a Python function that:
    - Takes a list of numbers
    - Returns the sum
    - Includes error handling
    - Has a docstring
    """,
    task_type="implementation"
)
```

### Use Case 2: Code Review

```python
code_to_review = """
def process_data(data):
    return data * 2
"""

review = call_llm(
    f"Review this code for issues:\n\n{code_to_review}",
    task_type="code-review"
)
```

### Use Case 3: Documentation

```python
docs = call_llm(
    "Write documentation for a REST API endpoint: POST /api/users",
    task_type="documentation"
)
```

### Use Case 4: Test Generation

```python
function_code = """
def add(a, b):
    return a + b
"""

tests = call_llm(
    f"Write unit tests for this function:\n\n{function_code}",
    task_type="testing"
)
```

---

## Integration with Ralph Workflow

### Reading Tasks from @fix_plan.md

```python
from pathlib import Path

def get_tasks():
    plan_file = Path('@fix_plan.md')
    if plan_file.exists():
        with open(plan_file) as f:
            tasks = [line.strip()[5:] for line in f if line.strip().startswith('- [ ]')]
        return tasks
    return []

# Get first task
tasks = get_tasks()
if tasks:
    task = tasks[0]
    solution = call_llm(f"Implement: {task}", task_type="implementation")
```

### Following Ralph Patterns

```python
# 1. Read task from @fix_plan.md
task = get_task_from_plan()

# 2. Generate solution using Ollama
solution = call_llm(f"Implement: {task}", task_type="implementation")

# 3. Write solution to file
write_solution_to_file(solution)

# 4. Test (your test logic)

# 5. Update @fix_plan.md (mark complete)
mark_task_complete(task)
```

---

## Model Selection

Models are automatically selected based on task type:

| Task Type        | Model Used | Why                       |
| ---------------- | ---------- | ------------------------- |
| `implementation` | codellama  | Best for code generation  |
| `testing`        | llama3.2   | Good for test writing     |
| `documentation`  | llama3.2   | Good for documentation    |
| `code-review`    | codellama  | Understands code patterns |
| `refactoring`    | codellama  | Code transformation       |

You can override the model:

```python
adapter = RalphOllamaAdapter()
result = adapter.generate(
    prompt="Your prompt",
    model="llama3.2:latest"  # Override default
)
```

---

## Environment Variables

Set these to configure the integration:

```bash
export RALPH_LLM_PROVIDER=ollama
export RALPH_LLM_MODEL=llama3.2:latest
export RALPH_OLLAMA_CONFIG=./config/ollama-config.json
```

---

## Troubleshooting

### Ollama Not Running

```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Models Not Available

```bash
# List available models
ollama list

# Pull a model
ollama pull llama3.2
```

### Import Errors

```bash
# Activate virtual environment
source venv/bin/activate

# Verify dependencies
pip list | grep requests
```

### Module Not Found

Make sure paths are set correctly:

```python
import sys
from pathlib import Path

from lib.path_utils import setup_paths
setup_paths()
```

---

## Next Steps

- See [QUICK-START.md](QUICK-START.md) for initial setup
- See [examples/ralph_workflow_demo.py](examples/ralph_workflow_demo.py) for complete example
- See [docs/INTEGRATION.md](docs/INTEGRATION.md) for detailed integration guide
- See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues

---

**Last Updated:** 2024
