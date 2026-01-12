# CI/CD Documentation

Complete guide to the CI/CD setup for Ralph Ollama Standalone project.

---

## Overview

The project uses GitHub Actions for continuous integration and deployment. The CI/CD pipeline includes:

- **Unit Tests** - Fast tests that don't require Ollama server
- **E2E Tests** - Integration tests that require Ollama server and models
- **Linting** - Code quality checks
- **Package Installation** - Verify package can be installed correctly

---

## Workflows

### 1. Unit Tests (`test.yml`)

**Purpose**: Run fast unit tests that don't require external services.

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**What it does**:
- Tests across Python versions: 3.8, 3.9, 3.10, 3.11, 3.12
- Runs pytest with coverage
- Skips e2e tests (run in separate workflow)

**Duration**: ~5-10 minutes

### 2. E2E Tests (`e2e.yml`)

**Purpose**: Run end-to-end integration tests with full Ollama setup.

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch (with optional skip Ollama setup)

**What it does**:
1. Sets up Python 3.11 environment
2. Installs Ollama server
3. Pulls test model (default: `llama3.2:1b`)
4. Runs UI e2e tests (`test_ui_e2e.py`)
5. Runs Ralph Loop e2e tests (`test_ralph_loop_e2e.py`)
6. Generates JUnit XML reports
7. Uploads test artifacts

**Duration**: ~15-25 minutes (depends on model download time)

**Artifacts**:
- Test reports (JUnit XML)
- Test logs
- Test project files (for debugging)

### 3. Linting (`lint.yml`)

**Purpose**: Check code quality and formatting.

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**What it does**:
- Runs `black` (format check)
- Runs `flake8` (linting)
- Runs `mypy` (type checking)
- Validates JSON config files

**Duration**: ~2-3 minutes

### 4. Package Installation (`package.yml`)

**Purpose**: Verify package can be installed correctly.

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**What it does**:
- Tests package installation on Python 3.8 and 3.11
- Verifies imports work
- Tests entry points

**Duration**: ~3-5 minutes

---

## E2E Test Setup

### Ollama Installation

The e2e workflow uses `.github/scripts/setup-ollama.sh` to:

1. Install Ollama using official installer
2. Start Ollama server in background
3. Pull test model (configurable via `OLLAMA_MODEL` env var)
4. Verify server is running

### Test Model Selection

**Default**: `llama3.2:1b` (small, fast model for CI)

**Fallback**: `phi3:mini` (if default fails)

**Custom**: Set `OLLAMA_MODEL` environment variable

### Test Execution

Tests are run via `.github/scripts/run-e2e-tests.sh` which:

1. Sets up test environment
2. Runs test script with proper arguments
3. Generates JUnit XML reports
4. Captures test output

---

## Running Tests Locally

### Unit Tests

```bash
# Run all unit tests
pytest tests/ -v -k "not test_ui_e2e and not test_ralph_loop_e2e"

# Run with coverage
pytest tests/ --cov=lib --cov=integration --cov-report=term-missing
```

### E2E Tests

**Prerequisites**:
- Ollama server running (`ollama serve`)
- At least one model pulled (`ollama pull llama3.2:1b`)

**Run UI E2E tests**:
```bash
# Auto-start server
python3 tests/test_ui_e2e.py

# Use existing server
python3 tests/test_ui_e2e.py --no-start-server

# With JUnit XML output
python3 tests/test_ui_e2e.py --junit-xml test-reports/ui-e2e.xml
```

**Run Ralph Loop E2E tests**:
```bash
# Auto-start server
python3 tests/test_ralph_loop_e2e.py

# Use existing server
python3 tests/test_ralph_loop_e2e.py --no-start-server

# With JUnit XML output
python3 tests/test_ralph_loop_e2e.py --junit-xml test-reports/ralph-loop-e2e.xml
```

---

## Test Reports

### JUnit XML Format

Both e2e test scripts support JUnit XML output via `--junit-xml` flag:

```bash
python3 tests/test_ui_e2e.py --junit-xml test-reports/ui-e2e.xml
```

The XML reports include:
- Test case names
- Pass/fail status
- Error messages
- Test timing

### GitHub Actions Integration

JUnit XML reports are automatically:
- Uploaded as artifacts
- Displayed in GitHub Actions UI
- Included in test summaries

---

## Troubleshooting CI Failures

### Ollama Installation Fails

**Symptoms**: `setup-ollama.sh` fails

**Solutions**:
- Check GitHub Actions logs for specific error
- Verify Ollama installer URL is accessible
- Try manual workflow dispatch with `skip_ollama_setup: true` to test other steps

### Model Pull Fails

**Symptoms**: Model download times out or fails

**Solutions**:
- Use smaller model: Set `OLLAMA_MODEL=phi3:mini`
- Increase timeout in workflow
- Check network connectivity in CI

### Tests Timeout

**Symptoms**: Tests don't complete within timeout

**Solutions**:
- Increase `TIMEOUT` environment variable
- Check if Ollama server is responding
- Verify model is loaded correctly

### Server Startup Fails

**Symptoms**: Flask server doesn't start

**Solutions**:
- Check port 5001 is available
- Verify Python dependencies are installed
- Check for import errors in logs

---

## Workflow Dependencies

```
┌─────────────┐
│   Push/PR   │
└──────┬──────┘
       │
       ├──► Unit Tests (test.yml)
       ├──► E2E Tests (e2e.yml)
       ├──► Linting (lint.yml)
       └──► Package Test (package.yml)
```

All workflows run in parallel for faster feedback.

---

## Environment Variables

### E2E Workflow

- `OLLAMA_MODEL`: Model to use for testing (default: `llama3.2:1b`)
- `BASE_URL`: Flask server URL (default: `http://localhost:5001`)
- `TIMEOUT`: Test timeout in seconds (default: 60 for UI, 120 for Ralph Loop)

### Test Workflow

- `RALPH_LLM_PROVIDER`: LLM provider (default: `ollama`)

---

## Manual Workflow Dispatch

You can manually trigger the e2e workflow:

1. Go to **Actions** tab in GitHub
2. Select **E2E Tests** workflow
3. Click **Run workflow**
4. Optionally check **Skip Ollama setup** to test without Ollama

---

## Best Practices

1. **Run tests locally first** - Don't wait for CI to catch issues
2. **Use small models for CI** - Faster execution, lower resource usage
3. **Monitor test duration** - Keep e2e tests under 30 minutes
4. **Check artifacts** - Download and review test reports
5. **Fix flaky tests** - Ensure tests are deterministic

---

## Performance Optimization

### Model Selection

- Use smallest available model for CI
- Cache models between runs (if possible)
- Consider model download time in timeout calculations

### Test Parallelization

- Unit tests run in parallel across Python versions
- E2E tests run sequentially (require shared Ollama server)
- Consider splitting e2e tests if they grow too large

### Timeout Configuration

- Unit tests: No timeout (fast)
- E2E tests: 30 minutes (includes model download)
- Individual test steps: 60-120 seconds

---

## Security Considerations

- No secrets required for e2e tests
- All tests run locally (no external API calls)
- Test projects are cleaned up after tests
- No sensitive data in test artifacts

---

## Future Improvements

- [ ] Cache Ollama models between CI runs
- [ ] Parallel e2e test execution
- [ ] Test result badges
- [ ] Automated test result notifications
- [ ] Performance benchmarking in CI

---

## Related Documentation

- [Test Suite README](../tests/README.md) - Test execution guide
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Setup Guide](SETUP.md) - Local development setup

---

**Last Updated**: 2025-01-12
