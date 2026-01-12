# Architecture Overview

High-level architecture of the Ralph Ollama integration.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Ralph Workflow Rules                      │
│         (.cursor/rules/ralph-core.mdc, etc.)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ LLM Request
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Provider Abstraction Layer                  │
│  (Adapter Pattern - routes to appropriate provider)          │
└───────────────┬───────────────────────┬─────────────────────┘
                │                       │
        ┌───────┴────────┐     ┌────────┴────────┐
        │                │     │                 │
        ▼                ▼     ▼                 ▼
┌──────────────┐  ┌──────────┐ ┌──────────┐  ┌──────────┐
│ Ollama       │  │ Cloud    │ │ Custom   │  │ Mock     │
│ (Local)      │  │ APIs     │ │ Provider │  │ (Testing)│
└──────────────┘  └──────────┘ └──────────┘  └──────────┘
       │
       │ HTTP API
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Ollama Server                            │
│              (localhost:11434)                              │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ llama3.2 │  │codellama │  │ mistral  │  │   phi3   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Overview

### 1. Configuration Layer

**Purpose:** Centralized configuration management

**Files:**
- `config/ollama-config.json` - Ollama server and model configurations
- `config/workflow-config.json` - Ralph workflow integration settings

**Key Features:**
- Model-specific parameters (temperature, context window, etc.)
- Task-based model selection rules
- Retry and timeout settings
- Cache configuration

---

### 2. Client Library

**Purpose:** Low-level API client for Ollama

**Files:**
- `lib/ollama_client.py` - Core client implementation

**Key Features:**
- HTTP API communication with Ollama
- Request/response handling
- Error handling and retries
- Model management utilities

**API:**
```python
client = OllamaClient()
result = client.generate(prompt, model="codellama")
```

---

### 3. Adapter Layer

**Purpose:** High-level interface compatible with Ralph workflow patterns

**Files:**
- `integration/ralph_ollama_adapter.py` - Adapter implementation

**Key Features:**
- Drop-in replacement for cloud APIs
- Task-based model selection
- Standardized response format
- Provider abstraction

**API:**
```python
adapter = RalphOllamaAdapter()
result = adapter.generate(prompt, task_type="implementation")
```

---

### 4. Scripts & Utilities

**Purpose:** Command-line tools and setup utilities

**Files:**
- `scripts/ralph-ollama.sh` - Main execution script
- `scripts/setup-ollama.sh` - Setup validation
- `scripts/model-manager.sh` - Model management

**Key Features:**
- Environment setup
- Validation and testing
- Model operations (list, pull, test)
- Workflow integration helpers

---

### 5. Documentation

**Purpose:** Comprehensive documentation and guides

**Files:**
- `README.md` - Overview and quick start
- `QUICK-START.md` - 5-minute setup guide
- `docs/SETUP.md` - Detailed setup instructions
- `docs/MODEL-GUIDE.md` - Model selection guide
- `docs/INTEGRATION.md` - Integration patterns
- `docs/TROUBLESHOOTING.md` - Common issues

---

## Data Flow

### Request Flow

```
1. Ralph Workflow Rule
   ↓
2. LLM Request (prompt, system_prompt, task_type)
   ↓
3. Adapter Layer (task-based model selection)
   ↓
4. Client Library (format request, add parameters)
   ↓
5. HTTP Request to Ollama API
   ↓
6. Ollama Server (process with selected model)
   ↓
7. HTTP Response (JSON)
   ↓
8. Client Library (parse response, extract tokens)
   ↓
9. Adapter Layer (format to standard response)
   ↓
10. Ralph Workflow (use response)
```

### Configuration Flow

```
Environment Variables
   ↓
Config Files (JSON)
   ↓
Client/Adapter Initialization
   ↓
Runtime Configuration
```

---

## Integration Points

### 1. Ralph Workflow Rules

The integration is designed to work seamlessly with existing Ralph workflow rules:

- `.cursor/rules/ralph-core.mdc` - Core workflow (unchanged)
- `.cursor/rules/ralph-status.mdc` - Status reporting (unchanged)
- Only the LLM provider changes (transparent to rules)

### 2. Environment Variables

Control provider selection via environment:

```bash
RALPH_LLM_PROVIDER=ollama
RALPH_OLLAMA_CONFIG=path/to/config.json
RALPH_LLM_MODEL=llama3.2
```

### 3. Configuration Files

JSON-based configuration for:
- Server connection settings
- Model parameters
- Task-to-model mapping
- Workflow settings

---

## Model Selection Strategy

### Automatic Selection

Based on task type:
- `implementation` → codellama
- `testing` → llama3.2
- `documentation` → llama3.2
- `code-review` → codellama
- `refactoring` → codellama

### Manual Selection

Override with explicit model parameter:
```python
adapter.generate(prompt, model="mistral")
```

### Fallback Chain

1. Explicit model parameter
2. Task-based selection (from config)
3. Default model (from config)
4. Hard-coded default (llama3.2)

---

## Error Handling

### Connection Errors

- Server not running → Clear error message
- Network errors → Retry with backoff
- Timeout → Configurable timeout settings

### Model Errors

- Model not found → List available models
- Model load failure → Graceful error
- Generation failure → Retry logic

### Configuration Errors

- Missing config → Default values
- Invalid JSON → Clear error message
- Missing models → Validation warnings

---

## Extension Points

### Adding New Models

1. Pull model: `ollama pull new-model`
2. Add to `config/ollama-config.json`
3. Configure parameters
4. (Optional) Add to task mappings

### Custom Adapters

Create custom adapters by:
1. Extending `RalphOllamaAdapter`
2. Overriding model selection
3. Adding custom logic

### Provider Plugins

The adapter pattern allows easy addition of:
- Other local LLM servers
- Hybrid providers
- Custom routing logic

---

## Performance Considerations

### Caching

- Response caching (configurable)
- Model parameter caching
- Config file caching

### Optimization

- Connection pooling (future)
- Batch requests (future)
- Streaming responses (configurable)

### Resource Management

- Model memory usage
- Server resource limits
- Concurrent request handling

---

## Security Considerations

### Local Execution

- All processing happens locally
- No data sent to external servers
- Complete privacy

### Configuration Security

- No secrets in config files
- Environment variable support
- Git-ignored sensitive data

---

## Future Enhancements

Potential additions:
- Streaming response support
- Batch request handling
- Model fine-tuning integration
- Performance monitoring
- Advanced caching strategies
- Multi-model ensemble

---

**Last Updated:** 2024
