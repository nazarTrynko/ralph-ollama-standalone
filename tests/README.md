# Test Suite

Tests for the Ralph Ollama integration.

## Test Files

### `test_connection.py`
Basic connection and functionality tests for Ollama integration.

**Usage:**
```bash
python3 tests/test_connection.py
```

**Tests:**
- Configuration loading
- Server connection
- Model listing
- Model generation

### `test_ui_e2e.py`
End-to-end tests for the web UI.

**Usage:**
```bash
# Start server automatically and run tests
python3 tests/test_ui_e2e.py

# Test against already-running server
python3 tests/test_ui_e2e.py --no-start-server

# Test against different URL
python3 tests/test_ui_e2e.py --url http://localhost:8080
```

**Tests:**
- Homepage loading
- Status endpoint
- Models endpoint
- Generate endpoint (with multiple test cases)
- Error handling
- Response validation

## Running All Tests

```bash
# Run connection tests
python3 tests/test_connection.py

# Run UI e2e tests
python3 tests/test_ui_e2e.py
```

## Test Requirements

- Ollama server running (for full tests)
- At least one model pulled (for generation tests)
- Python dependencies installed (`pip install -r requirements.txt`)

## Test Output

Tests provide colored output:
- ✅ Green: Test passed
- ❌ Red: Test failed
- ⚠️ Yellow: Warning (non-critical)

## Continuous Testing

You can run tests in a loop:

```bash
# Run e2e tests every 5 minutes
watch -n 300 python3 tests/test_ui_e2e.py
```
