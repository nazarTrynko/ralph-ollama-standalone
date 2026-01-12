#!/bin/bash
# Wrapper script to run e2e tests with proper environment setup
# Usage: run-e2e-tests.sh [ui|ralph-loop]

set -e

TEST_TYPE="${1:-ui}"
BASE_URL="${BASE_URL:-http://localhost:5001}"
TIMEOUT="${TIMEOUT:-60}"
REPORT_DIR="test-reports"

# Create report directory
mkdir -p "$REPORT_DIR"

echo "🧪 Running $TEST_TYPE E2E tests..."
echo "   Base URL: $BASE_URL"
echo "   Timeout: $TIMEOUT seconds"

# Determine test script
case "$TEST_TYPE" in
  ui)
    TEST_SCRIPT="tests/test_ui_e2e.py"
    REPORT_FILE="$REPORT_DIR/ui-e2e-results.txt"
    JUNIT_FILE="$REPORT_DIR/ui-e2e-junit.xml"
    ;;
  ralph-loop)
    TEST_SCRIPT="tests/test_ralph_loop_e2e.py"
    REPORT_FILE="$REPORT_DIR/ralph-loop-e2e-results.txt"
    JUNIT_FILE="$REPORT_DIR/ralph-loop-e2e-junit.xml"
    ;;
  *)
    echo "❌ Unknown test type: $TEST_TYPE"
    echo "   Valid options: ui, ralph-loop"
    exit 1
    ;;
esac

# Check if test script exists
if [ ! -f "$TEST_SCRIPT" ]; then
  echo "❌ Test script not found: $TEST_SCRIPT"
  exit 1
fi

# Run tests and capture output
echo "📝 Running tests..."
if python3 "$TEST_SCRIPT" \
  --url "$BASE_URL" \
  --timeout "$TIMEOUT" \
  --junit-xml "$JUNIT_FILE" \
  > "$REPORT_FILE" 2>&1; then
  TEST_EXIT_CODE=0
  echo "✅ Tests passed"
else
  TEST_EXIT_CODE=$?
  echo "❌ Tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Display summary
echo ""
echo "📊 Test Summary:"
echo "=================="
tail -20 "$REPORT_FILE" || echo "No output captured"

# Check if JUnit XML was generated
if [ -f "$JUNIT_FILE" ]; then
  echo "✅ JUnit XML report generated: $JUNIT_FILE"
else
  echo "⚠️  JUnit XML report not generated"
fi

exit $TEST_EXIT_CODE
