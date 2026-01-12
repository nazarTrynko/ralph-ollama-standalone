# Contributing to Ralph Ollama Integration

Guidelines for contributing improvements, fixes, and new features.

---

## Development Setup

### Prerequisites

1. Ollama installed and running
2. Python 3.8+ installed
3. At least one model pulled (e.g., `ollama pull llama3.2`)

### Setup

```bash
# Clone/navigate to repository
cd .cursor/ralph-ollama

# Install dependencies
pip install -r requirements.txt

# Run tests
python3 tests/test_connection.py

# Run examples
python3 examples/simple_example.py
```

---

## Code Structure

### Library (`lib/`)
- **ollama_client.py** - Core Ollama API client
- Keep low-level, focused on API interaction
- Include error handling and retry logic

### Integration (`integration/`)
- **ralph_ollama_adapter.py** - High-level adapter
- Ralph workflow compatibility layer
- Task-based model selection

### Scripts (`scripts/`)
- Shell scripts for setup and management
- Should be POSIX-compliant
- Include error handling

### Tests (`tests/`)
- Test scripts for validation
- Should be runnable independently
- Clear error messages

---

## Coding Standards

### Python

- Follow PEP 8 style guide
- Use type hints where appropriate
- Document functions with docstrings
- Include error handling
- Keep functions focused and small

### Shell Scripts

- Use `#!/bin/bash` or `#!/bin/sh`
- Check for dependencies
- Provide clear error messages
- Include help/usage information

### Documentation

- Update relevant docs when adding features
- Include examples in docstrings
- Update README.md for user-facing changes
- Update CHANGELOG.md for releases

---

## Adding Features

### New Models

1. Add model config to `config/ollama-config.json`
2. Update `docs/MODEL-GUIDE.md` with recommendations
3. Test with `scripts/model-manager.sh test <model>`

### New Scripts

1. Create in `scripts/` directory
2. Make executable: `chmod +x scripts/your-script.sh`
3. Add usage documentation
4. Update README.md if user-facing

### New Adapter Features

1. Add to `integration/ralph_ollama_adapter.py`
2. Update `integration/README.md`
3. Add examples to `examples/`
4. Test with existing workflows

---

## Testing

### Before Submitting

1. Run test script:
   ```bash
   python3 tests/test_connection.py
   ```

2. Test examples:
   ```bash
   python3 examples/simple_example.py
   ```

3. Test scripts:
   ```bash
   ./scripts/setup-ollama.sh
   ./scripts/model-manager.sh list
   ```

4. Verify documentation is updated

---

## Documentation Updates

When adding/changing features:

- **README.md** - User-facing overview
- **QUICK-START.md** - If affects setup
- **docs/SETUP.md** - If affects installation
- **docs/MODEL-GUIDE.md** - If adding models
- **docs/INTEGRATION.md** - If changing integration patterns
- **docs/TROUBLESHOOTING.md** - If addressing common issues
- **CHANGELOG.md** - For all changes
- **INDEX.md** - If adding new sections/files

---

## Commit Messages

Use clear, descriptive commit messages:

```
Add support for streaming responses
Fix timeout handling in OllamaClient
Update documentation for new model
```

---

## Pull Request Process

1. Create feature branch
2. Make changes with tests
3. Update documentation
4. Run all tests
5. Submit PR with description
6. Address feedback

---

## Questions?

- Check existing documentation
- Review examples
- Check architecture docs
- Ask in discussions/issues

---

**Last Updated:** 2024
