# Integration Guide

How to integrate Ollama with your Ralph workflow implementation.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Ralph Workflow                        │
│  (.cursor/rules/ralph-core.mdc, etc.)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ LLM Request
                     ▼
┌─────────────────────────────────────────────────────────┐
│              LLM Provider Abstraction                    │
│  (Routes to Ollama or Cloud API)                         │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Ollama API    │    │  Cloud APIs     │
│  (localhost)    │    │ (OpenAI, etc.)  │
└─────────────────┘    └─────────────────┘
```

---

## Integration Methods

### Method 1: Environment Variable Detection

**Simplest approach** - Check environment variables and route accordingly.

**Python Example:**
```python
import os
import json
import requests

def get_llm_response(prompt, system_prompt=None):
    provider = os.getenv('RALPH_LLM_PROVIDER', 'openai')
    
    if provider == 'ollama':
        return get_ollama_response(prompt, system_prompt)
    else:
        return get_openai_response(prompt, system_prompt)

def get_ollama_response(prompt, system_prompt=None):
    config_path = os.getenv('RALPH_OLLAMA_CONFIG', './config/ollama-config.json')
    
    with open(config_path) as f:
        config = json.load(f)
    
    model = os.getenv('RALPH_LLM_MODEL', config['defaultModel'])
    base_url = config['server']['baseUrl']
    
    # Build prompt
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{prompt}"
    
    # Make request
    response = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": config['models'][model]['parameters']
        },
        timeout=config['server'].get('timeout', 300)
    )
    
    response.raise_for_status()
    data = response.json()
    
    return data['response']
```

**Node.js Example:**
```javascript
const fs = require('fs');
const https = require('https');
const http = require('http');

function getLLMResponse(prompt, systemPrompt = null) {
  const provider = process.env.RALPH_LLM_PROVIDER || 'openai';
  
  if (provider === 'ollama') {
    return getOllamaResponse(prompt, systemPrompt);
  } else {
    return getOpenAIResponse(prompt, systemPrompt);
  }
}

async function getOllamaResponse(prompt, systemPrompt = null) {
  const configPath = process.env.RALPH_OLLAMA_CONFIG || 
    './config/ollama-config.json';
  
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const model = process.env.RALPH_LLM_MODEL || config.defaultModel;
  const baseUrl = new URL(config.server.baseUrl);
  
  const fullPrompt = systemPrompt ? `${systemPrompt}\n\n${prompt}` : prompt;
  
  const requestBody = JSON.stringify({
    model: model,
    prompt: fullPrompt,
    stream: false,
    options: config.models[model].parameters
  });
  
  return new Promise((resolve, reject) => {
    const client = baseUrl.protocol === 'https:' ? https : http;
    
    const req = client.request({
      hostname: baseUrl.hostname,
      port: baseUrl.port,
      path: '/api/generate',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(requestBody)
      }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const response = JSON.parse(data);
          resolve(response.response);
        } catch (e) {
          reject(e);
        }
      });
    });
    
    req.on('error', reject);
    req.write(requestBody);
    req.end();
  });
}
```

---

### Method 2: Configuration File Detection

Check for Ollama config file and use if present.

**Python Example:**
```python
import os
from pathlib import Path

def detect_llm_provider():
    """Auto-detect LLM provider based on configuration."""
    ollama_config = Path('config/workflow-config.json')
    
    if ollama_config.exists():
        import json
        with open(ollama_config) as f:
            config = json.load(f)
        
        if config.get('ollama', {}).get('enabled', False):
            return 'ollama'
    
    return 'openai'  # Default fallback
```

---

### Method 3: Plugin/Adapter Pattern

Create an LLM adapter interface.

**Python Example:**
```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, config_path=None):
        # Load config, initialize client
        pass
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        # Ollama implementation
        pass

class OpenAIProvider(LLMProvider):
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        # OpenAI implementation
        pass

# Factory
def create_provider():
    if os.getenv('RALPH_LLM_PROVIDER') == 'ollama':
        return OllamaProvider()
    return OpenAIProvider()
```

---

## Configuration Integration

### Loading Configuration

**Python:**
```python
import json
import os

def load_ollama_config():
    config_path = os.getenv(
        'RALPH_OLLAMA_CONFIG',
        './config/ollama-config.json'
    )
    
    with open(config_path) as f:
        return json.load(f)

def load_workflow_config():
    config_path = os.getenv(
        'RALPH_WORKFLOW_CONFIG',
        './config/workflow-config.json'
    )
    
    with open(config_path) as f:
        return json.load(f)
```

---

## Model Selection

### Task-Based Model Selection

Use workflow config for automatic model selection:

```python
def select_model_for_task(task_type, workflow_config):
    """Select model based on task type."""
    if not workflow_config.get('workflow', {}).get('autoSelectModel', False):
        return workflow_config.get('ollama', {}).get('defaultModel', 'llama3.2')
    
    task_config = workflow_config.get('workflow', {}).get('tasks', {}).get(task_type, {})
    return task_config.get('preferredModel') or 'llama3.2'
```

---

## Error Handling

### Retry Logic

Implement retry with backoff:

```python
import time
import requests

def get_ollama_response_with_retry(prompt, max_attempts=3, backoff_ms=1000):
    config = load_ollama_config()
    retry_config = config.get('retry', {})
    
    max_attempts = retry_config.get('maxAttempts', max_attempts)
    backoff_ms = retry_config.get('backoffMs', backoff_ms)
    
    for attempt in range(max_attempts):
        try:
            return get_ollama_response(prompt)
        except requests.exceptions.RequestException as e:
            if attempt == max_attempts - 1:
                raise
            
            wait_time = backoff_ms * (2 ** attempt) if retry_config.get('exponentialBackoff') else backoff_ms
            time.sleep(wait_time / 1000.0)
```

---

## Caching Integration

### Response Caching

Cache responses to avoid repeated API calls:

```python
import hashlib
import json
import os
from pathlib import Path

cache_dir = Path('state/cache')

def get_cache_key(prompt, model, params):
    """Generate cache key from prompt and parameters."""
    key_data = f"{prompt}:{model}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def get_cached_response(prompt, model, params):
    """Get cached response if available."""
    if not config.get('cache', {}).get('enabled', False):
        return None
    
    cache_key = get_cache_key(prompt, model, params)
    cache_file = cache_dir / f"{cache_key}.json"
    
    if cache_file.exists():
        with open(cache_file) as f:
            cached = json.load(f)
        
        # Check TTL
        import time
        ttl = config.get('cache', {}).get('ttlSeconds', 3600)
        if time.time() - cached['timestamp'] < ttl:
            return cached['response']
    
    return None

def cache_response(prompt, model, params, response):
    """Cache response."""
    if not config.get('cache', {}).get('enabled', False):
        return
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = get_cache_key(prompt, model, params)
    cache_file = cache_dir / f"{cache_key}.json"
    
    with open(cache_file, 'w') as f:
        json.dump({
            'response': response,
            'timestamp': time.time()
        }, f)
```

---

## Testing Integration

### Test Ollama Connection

```python
def test_ollama_connection():
    """Test if Ollama is accessible."""
    try:
        config = load_ollama_config()
        base_url = config['server']['baseUrl']
        
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        
        return True
    except:
        return False
```

---

## Status Reporting Integration

Ralph status blocks should work the same regardless of provider:

```python
def generate_ralph_status(status, tasks_completed, files_modified, 
                         tests_status, work_type, exit_signal, recommendation):
    """Generate Ralph status block (same format for all providers)."""
    return f"""---RALPH_STATUS---
STATUS: {status}
TASKS_COMPLETED_THIS_LOOP: {tasks_completed}
FILES_MODIFIED: {files_modified}
TESTS_STATUS: {tests_status}
WORK_TYPE: {work_type}
EXIT_SIGNAL: {exit_signal}
RECOMMENDATION: {recommendation}
---END_RALPH_STATUS---"""
```

---

## Best Practices

1. **Graceful Fallback**: Always have a fallback to cloud API if Ollama fails
2. **Error Handling**: Handle connection errors, timeouts, model errors
3. **Logging**: Log provider used, model, response times
4. **Configuration**: Make configuration easily overridable
5. **Testing**: Test both Ollama and cloud providers
6. **Performance**: Monitor response times, adjust models/config as needed

---

## Example: Full Integration

See `scripts/ralph-runner.py` (if created) for a complete integration example.

---

**Last Updated:** 2024
