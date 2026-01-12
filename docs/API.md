# API Reference

Complete API reference for Ralph Ollama integration.

---

## Core Classes

### OllamaClient

Main client for interacting with Ollama API.

#### Constructor

```python
OllamaClient(config_path: Optional[str] = None) -> None
```

**Parameters:**
- `config_path` (Optional[str]): Path to `ollama-config.json`. If `None`, uses default or environment variable.

**Raises:**
- `OllamaConfigError`: If configuration file is missing or invalid.

**Example:**
```python
from lib.ollama_client import OllamaClient

# Use default config
client = OllamaClient()

# Use custom config
client = OllamaClient('/path/to/config.json')
```

#### Methods

##### check_server()

Check if Ollama server is running.

```python
check_server() -> bool
```

**Returns:**
- `bool`: `True` if server is accessible, `False` otherwise.

**Example:**
```python
if client.check_server():
    print("Server is running")
else:
    print("Server is not running")
```

##### list_models()

List available models on Ollama server.

```python
list_models() -> List[str]
```

**Returns:**
- `List[str]`: List of model names.

**Raises:**
- `OllamaConnectionError`: If server is not accessible.
- `OllamaServerError`: If server returns an error.
- `OllamaTimeoutError`: If request times out.

**Example:**
```python
models = client.list_models()
print(f"Available models: {', '.join(models)}")
```

##### generate()

Generate response from Ollama.

```python
generate(
    prompt: str,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    stream: bool = False,
    **kwargs: Any
) -> Dict[str, Any]
```

**Parameters:**
- `prompt` (str): The user prompt.
- `model` (Optional[str]): Model name. If `None`, uses default from config.
- `system_prompt` (Optional[str]): Optional system prompt.
- `stream` (bool): Whether to stream the response (not yet implemented).
- `**kwargs`: Additional parameters (temperature, top_p, etc.).

**Returns:**
- `Dict[str, Any]`: Dictionary with keys:
  - `response` (str): Generated text.
  - `model` (str): Model used.
  - `tokens` (dict): Token usage information.
  - `done` (bool): Whether generation is complete.

**Raises:**
- `OllamaConnectionError`: If server is not running.
- `OllamaModelError`: If model is not found.
- `OllamaServerError`: If server returns an error.
- `OllamaTimeoutError`: If request times out.

**Example:**
```python
result = client.generate(
    prompt="Write a Python function to calculate factorial",
    model="codellama",
    system_prompt="You are a helpful coding assistant",
    temperature=0.7
)

print(result['response'])
print(f"Tokens used: {result['tokens']['total']}")
```

##### test_model()

Test if a model works.

```python
test_model(model: Optional[str] = None) -> bool
```

**Parameters:**
- `model` (Optional[str]): Model name. If `None`, uses default.

**Returns:**
- `bool`: `True` if model works, `False` otherwise.

**Example:**
```python
if client.test_model("llama3.2"):
    print("Model is working")
```

---

### RalphOllamaAdapter

High-level adapter for Ralph workflow integration.

#### Constructor

```python
RalphOllamaAdapter(config_path: Optional[str] = None) -> None
```

**Parameters:**
- `config_path` (Optional[str]): Path to config file. If `None`, uses default.

**Example:**
```python
from integration.ralph_ollama_adapter import RalphOllamaAdapter

adapter = RalphOllamaAdapter()
```

#### Methods

##### generate()

Generate response with task-based model selection.

```python
generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    task_type: Optional[str] = None,
    **kwargs: Any
) -> Dict[str, Any]
```

**Parameters:**
- `prompt` (str): User prompt.
- `system_prompt` (Optional[str]): Optional system prompt.
- `model` (Optional[str]): Model name. If `None`, auto-selects based on `task_type`.
- `task_type` (Optional[str]): Task type for automatic model selection:
  - `"implementation"`: Code generation tasks
  - `"testing"`: Test writing tasks
  - `"documentation"`: Documentation tasks
  - `"code-review"`: Code review tasks
  - `"refactoring"`: Refactoring tasks
- `**kwargs`: Additional parameters.

**Returns:**
- `Dict[str, Any]`: Dictionary with keys:
  - `content` (str): Generated text.
  - `model` (str): Model used.
  - `provider` (str): Always `"ollama"`.
  - `tokens` (dict): Token usage information.
  - `done` (bool): Whether generation is complete.

**Example:**
```python
result = adapter.generate(
    prompt="Implement a factorial function",
    task_type="implementation"
)
print(result['content'])
```

##### check_available()

Check if Ollama is available and ready.

```python
check_available() -> bool
```

**Returns:**
- `bool`: `True` if Ollama is available, `False` otherwise.

##### get_default_model()

Get default model name.

```python
get_default_model() -> str
```

**Returns:**
- `str`: Default model name.

---

## Convenience Functions

### get_llm_response()

Convenience function for getting LLM response.

```python
get_llm_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    config_path: Optional[str] = None
) -> str
```

**Parameters:**
- `prompt` (str): The user prompt.
- `system_prompt` (Optional[str]): Optional system prompt.
- `model` (Optional[str]): Model name. If `None`, uses default from config.
- `config_path` (Optional[str]): Path to config file. If `None`, uses default or env var.

**Returns:**
- `str`: The generated response text.

**Example:**
```python
from lib.ollama_client import get_llm_response

response = get_llm_response("Hello, world!", model="llama3.2")
print(response)
```

### call_llm()

Convenience function for LLM calls in Ralph workflow.

```python
call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    task_type: Optional[str] = None
) -> str
```

**Parameters:**
- `prompt` (str): User prompt.
- `system_prompt` (Optional[str]): Optional system prompt.
- `model` (Optional[str]): Model name (optional).
- `task_type` (Optional[str]): Task type for model selection (optional).

**Returns:**
- `str`: Generated response text.

**Raises:**
- `OllamaConfigError`: If Ollama is not configured.

**Example:**
```python
from integration.ralph_ollama_adapter import call_llm

response = call_llm(
    "Write a test for this function",
    task_type="testing"
)
```

### create_ralph_llm_provider()

Factory function to create LLM provider based on environment.

```python
create_ralph_llm_provider() -> Optional[RalphOllamaAdapter]
```

**Returns:**
- `Optional[RalphOllamaAdapter]`: Adapter if Ollama is configured, `None` otherwise.

**Example:**
```python
from integration.ralph_ollama_adapter import create_ralph_llm_provider

provider = create_ralph_llm_provider()
if provider:
    result = provider.generate("Hello", task_type="implementation")
```

---

## Exception Classes

### OllamaError

Base exception for all Ollama-related errors.

```python
class OllamaError(Exception):
    pass
```

### OllamaConnectionError

Raised when connection to Ollama server fails.

```python
class OllamaConnectionError(OllamaError):
    def __init__(self, message: str, server_url: str = None):
        self.server_url = server_url
```

### OllamaServerError

Raised when Ollama server is unavailable or returns an error.

```python
class OllamaServerError(OllamaError):
    def __init__(self, message: str, server_url: str = None, status_code: int = None):
        self.server_url = server_url
        self.status_code = status_code
```

### OllamaModelError

Raised when model-related errors occur.

```python
class OllamaModelError(OllamaError):
    def __init__(self, message: str, model: str = None, available_models: list = None):
        self.model = model
        self.available_models = available_models
```

### OllamaConfigError

Raised when configuration errors occur.

```python
class OllamaConfigError(OllamaError):
    def __init__(self, message: str, config_path: str = None):
        self.config_path = config_path
```

### OllamaTimeoutError

Raised when request times out.

```python
class OllamaTimeoutError(OllamaError):
    def __init__(self, message: str, timeout: float = None):
        self.timeout = timeout
```

---

## Configuration Functions

### get_config_path()

Get Ollama config path from env or default.

```python
get_config_path() -> Path
```

**Returns:**
- `Path`: Path to configuration file.

### load_and_validate_config()

Load and validate configuration file.

```python
load_and_validate_config(config_path: Path) -> Dict[str, Any]
```

**Parameters:**
- `config_path` (Path): Path to configuration file.

**Returns:**
- `Dict[str, Any]`: Validated configuration dictionary.

**Raises:**
- `FileNotFoundError`: If config file doesn't exist.
- `ConfigValidationError`: If config validation fails.

---

## Logging

### setup_logging()

Set up logging configuration.

```python
setup_logging(
    level: str = 'INFO',
    log_path: Optional[Path] = None,
    log_requests: bool = False,
    log_responses: bool = False,
    format_string: Optional[str] = None
) -> logging.Logger
```

**Parameters:**
- `level` (str): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
- `log_path` (Optional[Path]): Optional path to log file.
- `log_requests` (bool): Whether to log requests.
- `log_responses` (bool): Whether to log responses.
- `format_string` (Optional[str]): Custom format string.

**Returns:**
- `logging.Logger`: Configured logger instance.

### get_logger()

Get logger instance.

```python
get_logger(name: Optional[str] = None) -> logging.Logger
```

**Parameters:**
- `name` (Optional[str]): Optional logger name (defaults to 'ralph_ollama').

**Returns:**
- `logging.Logger`: Logger instance.

---

## Error Handling Examples

### Handling Connection Errors

```python
from lib.ollama_client import OllamaClient
from lib.exceptions import OllamaConnectionError

try:
    client = OllamaClient()
    result = client.generate("Hello")
except OllamaConnectionError as e:
    print(f"Connection error: {e}")
    print(f"Server URL: {e.server_url}")
    print("Start Ollama server with: ollama serve")
```

### Handling Model Errors

```python
from lib.exceptions import OllamaModelError

try:
    result = client.generate("Hello", model="nonexistent")
except OllamaModelError as e:
    print(f"Model error: {e}")
    print(f"Model: {e.model}")
    if e.available_models:
        print(f"Available models: {', '.join(e.available_models)}")
```

### Handling Timeout Errors

```python
from lib.exceptions import OllamaTimeoutError

try:
    result = client.generate("Hello")
except OllamaTimeoutError as e:
    print(f"Timeout error: {e}")
    print(f"Timeout: {e.timeout}s")
    print("Try increasing timeout in config")
```

---

**Last Updated:** 2025-01-12
