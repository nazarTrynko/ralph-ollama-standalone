# Model Selection Guide

Guide for selecting the right Ollama model for different Ralph workflow tasks.

---

## Model Comparison

| Model | Size | Context | Speed | Best For | Code Quality |
|-------|------|---------|-------|----------|--------------|
| **llama3.2** | 2.0GB | 8K | ⭐⭐⭐⭐ | General tasks | ⭐⭐⭐⭐ |
| **codellama** | 3.8GB | 16K | ⭐⭐⭐ | Code generation | ⭐⭐⭐⭐⭐ |
| **mistral** | 4.1GB | 8K | ⭐⭐⭐⭐ | Reasoning, planning | ⭐⭐⭐⭐ |
| **phi3** | 2.3GB | 4K | ⭐⭐⭐⭐⭐ | Quick tasks | ⭐⭐⭐ |

---

## Task-Specific Recommendations

### Implementation (Code Writing)

**Best:** `codellama`
- Excellent code generation
- Large context window (16K)
- Understands code patterns
- Good at following style guides

**Example use:**
```bash
./scripts/ralph-ollama.sh --model codellama
```

**When to use:**
- Writing new features
- Complex implementations
- Code that needs to follow patterns
- Large files (>1000 lines)

---

### Code Review

**Best:** `codellama`
- Understands code semantics
- Good at spotting issues
- Can suggest improvements
- Handles large contexts

**When to use:**
- Reviewing pull requests
- Finding bugs
- Suggesting refactors
- Code quality checks

---

### Documentation

**Best:** `llama3.2`
- Good language understanding
- Clear explanations
- Handles markdown well
- Faster than codellama

**Fallback:** `phi3`
- Very fast
- Good for simple docs
- Lower quality but acceptable

**When to use:**
- Writing README files
- API documentation
- Comments and docstrings
- User guides

---

### Refactoring

**Best:** `codellama`
- Understands code structure
- Can preserve functionality
- Good at pattern matching
- Large context for big refactors

**Fallback:** `mistral`
- Better reasoning
- Good for architectural changes

**When to use:**
- Restructuring code
- Improving code quality
- Modernizing patterns
- Breaking down large functions

---

### Testing

**Best:** `llama3.2`
- Balanced approach
- Good at understanding requirements
- Can write clear tests

**Alternative:** `codellama`
- Better for complex test scenarios
- Good at mocking patterns

**When to use:**
- Writing unit tests
- Integration tests
- Test fixtures
- Test documentation

---

### Architecture & Planning

**Best:** `mistral`
- Strong reasoning capabilities
- Good at system design
- Can handle complex decisions

**Fallback:** `llama3.2`
- Good general reasoning
- Faster responses

**When to use:**
- System design
- Planning features
- Technical decisions
- Architecture reviews

---

### Quick Fixes

**Best:** `phi3`
- Very fast responses
- Good enough for simple fixes
- Low resource usage

**When to use:**
- Simple bug fixes
- Typo corrections
- Formatting issues
- Quick edits

---

## Performance Considerations

### Response Time

**Fastest to Slowest:**
1. phi3 (~1-3 seconds)
2. llama3.2 (~2-5 seconds)
3. mistral (~3-6 seconds)
4. codellama (~4-8 seconds)

*Times vary based on prompt length, system resources, and model size*

### Resource Usage

**Memory (RAM):**
- phi3: ~3-4GB
- llama3.2: ~4-5GB
- codellama: ~6-8GB
- mistral: ~6-8GB

**Disk Space:**
- phi3: 2.3GB
- llama3.2: 2.0GB
- codellama: 3.8GB
- mistral: 4.1GB

### Context Window

Models have different context window limits:

- **phi3:** 4K tokens (~3000 words)
- **llama3.2:** 8K tokens (~6000 words)
- **codellama:** 16K tokens (~12000 words)
- **mistral:** 8K tokens (~6000 words)

Choose based on your codebase/file sizes.

---

## Model Selection Strategy

### Automatic Selection (Recommended)

Configure `config/workflow-config.json` with task-based model selection:

```json
{
  "workflow": {
    "autoSelectModel": true,
    "modelSelectionStrategy": "task-based",
    "tasks": {
      "implementation": {
        "preferredModel": "codellama",
        "fallbackModel": "llama3.2"
      }
    }
  }
}
```

### Manual Selection

Override model per task:

```bash
# Use specific model
./scripts/ralph-ollama.sh --model codellama

# Or set environment variable
export RALPH_LLM_MODEL=codellama
```

---

## Testing Models

Test models before using in production:

```bash
# Test a model
./scripts/model-manager.sh test llama3.2

# Compare models
./scripts/model-manager.sh test codellama
./scripts/model-manager.sh test llama3.2
```

---

## Model Updates

Keep models updated:

```bash
# Pull latest version
ollama pull llama3.2

# Check for updates
ollama list
```

---

## Custom Models

You can create custom models for specific use cases:

```bash
# Create Modelfile (see Ollama docs)
ollama create my-ralph-model -f Modelfile

# Use custom model
./scripts/ralph-ollama.sh --model my-ralph-model
```

---

## Recommendations by Project Type

### Small Projects (< 10K LOC)
- **Primary:** llama3.2 or phi3
- **Reason:** Fast, efficient, sufficient quality

### Medium Projects (10K - 100K LOC)
- **Primary:** llama3.2
- **Code tasks:** codellama
- **Reason:** Balance of speed and quality

### Large Projects (> 100K LOC)
- **Primary:** codellama
- **Docs/Planning:** llama3.2 or mistral
- **Reason:** Better code understanding, larger context

### Code-Heavy Projects
- **Always:** codellama
- **Reason:** Best code generation and understanding

### Documentation-Heavy Projects
- **Primary:** llama3.2
- **Quick edits:** phi3
- **Reason:** Language understanding, speed

---

**Last Updated:** 2024
