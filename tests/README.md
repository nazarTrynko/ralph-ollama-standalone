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

# Generate JUnit XML report (for CI/CD)
python3 tests/test_ui_e2e.py --junit-xml test-reports/ui-e2e.xml
```

**Tests:**

- Homepage loading
- Status endpoint
- Models endpoint
- Generate endpoint (with multiple test cases)
- Error handling
- Response validation

### `test_ralph_loop_e2e.py`

End-to-end tests for the Ralph Loop functionality.

**Usage:**

```bash
# Start server automatically and run tests
python3 tests/test_ralph_loop_e2e.py

# Test against already-running server
python3 tests/test_ralph_loop_e2e.py --no-start-server

# Test against different URL
python3 tests/test_ralph_loop_e2e.py --url http://localhost:8080

# Generate JUnit XML report (for CI/CD)
python3 tests/test_ralph_loop_e2e.py --junit-xml test-reports/ralph-loop-e2e.xml
```

**Tests:**

- Starting Ralph loops (phase-by-phase and non-stop modes)
- Getting loop status
- Project initialization
- File tracking
- Pausing and resuming loops
- Switching between modes
- Stopping loops
- Error handling for all endpoints
- File list retrieval

### `test_ui_browser_e2e.py`

Browser-based end-to-end tests using Playwright that test the actual web UI.

**Prerequisites:**

```bash
pip install playwright
playwright install chromium
```

**Usage:**

```bash
# Start server automatically and run browser tests
python3 tests/test_ui_browser_e2e.py

# Test against already-running server
python3 tests/test_ui_browser_e2e.py --no-start-server

# Run in headed mode (see browser)
python3 tests/test_ui_browser_e2e.py --headed

# Test against different URL
python3 tests/test_ui_browser_e2e.py --url http://localhost:8080
```

**Tests:**

- Homepage loads correctly
- Tab switching functionality
- Complete prompt workflow (form fill, submit, response display)
- Ralph Loop project creation
- Status updates in real-time
- Control buttons (pause, resume, stop, mode switch)
- File list updates
- UI element visibility and interactions

**Features:**

- Screenshots on test failures
- Video recording (in headed mode)
- Real browser interactions
- Visual verification
- Automatic cleanup of test projects after test run

**Test Project Cleanup:**

Browser e2e tests automatically create and clean up test projects in the `projects/` directory. Test projects are tracked and removed after tests complete. Test-generated projects are ignored by git (see `.gitignore` patterns: `projects/Test*`, `projects/*Test*`).

## Running All Tests

```bash
# Run connection tests
python3 tests/test_connection.py

# Run UI e2e tests
python3 tests/test_ui_e2e.py

# Run Ralph Loop e2e tests
python3 tests/test_ralph_loop_e2e.py

# Run browser e2e tests (requires Playwright)
python3 tests/test_ui_browser_e2e.py
```

## Test Requirements

- Ollama server running (for full tests)
- At least one model pulled (for generation tests)
- Python dependencies installed (`pip install -r requirements.txt`)
- Playwright installed (for browser tests):
  ```bash
  pip install playwright
  playwright install chromium
  ```

## Test Output

Tests provide colored output:

- ✅ Green: Test passed
- ❌ Red: Test failed
- ⚠️ Yellow: Warning (non-critical)

## Continuous Testing

You can run tests in a loop:

```bash
# Run UI e2e tests every 5 minutes
watch -n 300 python3 tests/test_ui_e2e.py

# Run Ralph Loop e2e tests every 5 minutes
watch -n 300 python3 tests/test_ralph_loop_e2e.py
```

## Test Coverage

### UI Tests (`test_ui_e2e.py`)

- Basic UI functionality
- API endpoint validation
- Error handling
- Response generation

### Ralph Loop Tests (`test_ralph_loop_e2e.py`)

- Complete Ralph Loop workflow
- Project initialization
- Phase execution
- Mode switching
- File tracking
- Control operations (start, pause, resume, stop)

### Browser Tests (`test_ui_browser_e2e.py`)

- Actual browser-based UI testing
- Complete user workflows
- Real-time UI updates
- Visual verification
- Form interactions
- Button clicks and navigation

## CI/CD Integration

E2E tests are automatically run in GitHub Actions CI/CD pipeline:

- **Workflow**: `.github/workflows/e2e.yml`
- **Triggers**: Push/PR to main/develop branches
- **Features**:
  - Automatic Ollama server setup
  - Model installation
  - JUnit XML report generation
  - Test artifact upload
  - Browser tests with Playwright
  - Screenshot and video capture on failures

**Test Types:**

1. **API Tests** (`test_ui_e2e.py`, `test_ralph_loop_e2e.py`) - Fast HTTP endpoint validation
2. **Browser Tests** (`test_ui_browser_e2e.py`) - Full UI workflow testing with Playwright

See [CI/CD Documentation](../docs/CI_CD.md) for complete details.
