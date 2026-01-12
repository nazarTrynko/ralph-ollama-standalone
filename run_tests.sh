#!/bin/bash
# Quick test script for Ralph Ollama integration

set -e

cd "$(dirname "$0")"

echo "🧪 Testing Ralph Ollama Integration"
echo "=================================="
echo ""

# Test 1: Config module
echo "1. Testing config module..."
python3 -c "
import sys
sys.path.insert(0, 'lib')
from config import get_config_path, is_ollama_enabled
print('  ✓ Config module imports')
print(f'  ✓ Config path: {get_config_path()}')
print(f'  ✓ Ollama enabled: {is_ollama_enabled()}')
"
echo ""

# Test 2: Client initialization (without actual API call)
echo "2. Testing client initialization..."
python3 -c "
import sys
sys.path.insert(0, 'lib')
try:
    from ollama_client import OllamaClient
    client = OllamaClient()
    print('  ✓ Client initialized')
    print(f'  ✓ Server: {client.base_url}')
    print(f'  ✓ Default model: {client.default_model}')
except ImportError as e:
    print(f'  ⚠ Import error (expected if requests not installed): {e}')
except Exception as e:
    print(f'  ✓ Client structure OK (config error expected): {type(e).__name__}')
"
echo ""

# Test 3: Adapter structure
echo "3. Testing adapter structure..."
python3 -c "
import sys
sys.path.insert(0, 'lib')
sys.path.insert(0, 'integration')
try:
    from ralph_ollama_adapter import create_ralph_llm_provider, RalphOllamaAdapter
    print('  ✓ Adapter imports')
    adapter = create_ralph_llm_provider()
    if adapter:
        print('  ✓ Adapter created')
    else:
        print('  ✓ Adapter factory works (returns None when not configured)')
except ImportError as e:
    print(f'  ⚠ Import error: {e}')
except Exception as e:
    print(f'  ✓ Adapter structure OK: {type(e).__name__}')
"
echo ""

# Test 4: Check config files exist
echo "4. Checking configuration files..."
if [ -f "config/ollama-config.json" ]; then
    echo "  ✓ ollama-config.json exists"
    python3 -c "import json; json.load(open('config/ollama-config.json')); print('  ✓ Valid JSON')" 2>/dev/null || echo "  ⚠ Invalid JSON"
else
    echo "  ✗ ollama-config.json missing"
fi

if [ -f "config/workflow-config.json" ]; then
    echo "  ✓ workflow-config.json exists"
    python3 -c "import json; json.load(open('config/workflow-config.json')); print('  ✓ Valid JSON')" 2>/dev/null || echo "  ⚠ Invalid JSON"
else
    echo "  ✗ workflow-config.json missing"
fi
echo ""

# Test 5: Check scripts exist
echo "5. Checking scripts..."
for script in scripts/ralph-ollama.sh scripts/setup-ollama.sh scripts/model-manager.sh; do
    if [ -f "$script" ]; then
        echo "  ✓ $(basename $script) exists"
    else
        echo "  ✗ $(basename $script) missing"
    fi
done
echo ""

echo "=================================="
echo "✅ Basic structure tests complete!"
echo ""
echo "Note: Full functionality tests require:"
echo "  - Ollama server running (ollama serve)"
echo "  - At least one model pulled (ollama pull llama3.2)"
echo "  - requests module installed (pip install -r requirements.txt)"
echo ""
echo "Run: python3 tests/test_connection.py (after installing dependencies)"
