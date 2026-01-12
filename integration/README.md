# Integration Examples

Practical examples for integrating Ollama with Ralph workflow.

---

## Adapter Pattern

**File:** `ralph_ollama_adapter.py`

A drop-in adapter that provides a standardized interface for using Ollama with Ralph workflows.

### Usage

```python
from ralph_ollama_adapter import RalphOllamaAdapter, create_ralph_llm_provider

# Option 1: Direct usage
adapter = RalphOllamaAdapter()
result = adapter.generate(
    prompt="Write a function to calculate factorial",
    task_type="implementation"  # Auto-selects codellama
)

print(result['content'])

# Option 2: Factory function (checks environment)
adapter = create_ralph_llm_provider()
if adapter:
    result = adapter.generate(prompt="Review this code")
    print(result['content'])

# Option 3: Convenience function
from ralph_ollama_adapter import call_llm

response = call_llm(
    prompt="Write tests for this function",
    task_type="testing"
)
```

### Integration with Existing Code

If you have existing code that uses cloud APIs, you can replace it like this:

**Before (cloud API):**
```python
response = openai_client.generate(prompt, system_prompt)
```

**After (Ollama adapter):**
```python
from ralph_ollama_adapter import call_llm

response = call_llm(prompt, system_prompt)
```

The adapter handles all the Ollama-specific details.

---

## Environment-Based Selection

The adapter can automatically select between Ollama and cloud providers:

```python
from ralph_ollama_adapter import create_ralph_llm_provider

# This will use Ollama if RALPH_LLM_PROVIDER=ollama is set
# Otherwise, returns None (you'd use cloud API)
adapter = create_ralph_llm_provider()

if adapter:
    # Use Ollama
    result = adapter.generate(prompt)
else:
    # Fall back to cloud API
    result = cloud_client.generate(prompt)
```

---

## Task-Based Model Selection

The adapter automatically selects the best model for each task type:

```python
adapter = RalphOllamaAdapter()

# Implementation tasks → codellama
result = adapter.generate(
    prompt="Implement this feature",
    task_type="implementation"
)

# Documentation tasks → llama3.2
result = adapter.generate(
    prompt="Write documentation",
    task_type="documentation"
)

# Testing tasks → llama3.2
result = adapter.generate(
    prompt="Write unit tests",
    task_type="testing"
)
```

Task types are configured in `config/workflow-config.json`.

---

## Response Format

The adapter returns responses in a standardized format:

```python
{
    'content': 'The generated text response',
    'model': 'codellama',  # Model used
    'provider': 'ollama',  # Provider identifier
    'tokens': {
        'prompt': 100,
        'completion': 200,
        'total': 300
    },
    'done': True
}
```

This format is compatible with common LLM provider interfaces.

---

## Error Handling

The adapter includes error handling:

```python
adapter = RalphOllamaAdapter()

# Check if Ollama is available
if not adapter.check_available():
    print("Ollama server not running")
    # Fall back to cloud API or exit
    return

try:
    result = adapter.generate(prompt)
except RuntimeError as e:
    print(f"Error: {e}")
    # Handle error (retry, fallback, etc.)
```

---

## Integration Patterns

### Pattern 1: Direct Replacement

Replace cloud API calls directly:

```python
# Old
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(...)

# New
from ralph_ollama_adapter import call_llm
response = call_llm(prompt, system_prompt)
```

### Pattern 2: Provider Abstraction

Use adapter as part of provider abstraction:

```python
def get_llm_provider():
    adapter = create_ralph_llm_provider()
    if adapter:
        return adapter
    return CloudLLMProvider()

provider = get_llm_provider()
result = provider.generate(prompt)
```

### Pattern 3: Environment-Based

Use environment variables to control provider:

```bash
# Use Ollama
export RALPH_LLM_PROVIDER=ollama
export RALPH_OLLAMA_CONFIG=./config/ollama-config.json

# Run your script
python your_script.py
```

---

## See Also

- `../docs/INTEGRATION.md` - Detailed integration guide
- `../examples/simple_example.py` - Basic usage examples
- `../lib/ollama_client.py` - Low-level client API

---

**Last Updated:** 2024
