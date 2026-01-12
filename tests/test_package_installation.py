#!/usr/bin/env python3
"""
Test package installation and imports.
Verifies that the package can be installed and all modules can be imported.
"""

import sys
import importlib
from pathlib import Path

# Add project root to path for testing (simulates package installation)
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_core_imports():
    """Test that core modules can be imported."""
    print("Testing core module imports...")
    
    try:
        from lib import OllamaClient, get_llm_response
        from lib.config import get_config_path, is_ollama_enabled
        print("  ✅ lib package imports work")
        return True
    except ImportError as e:
        error_msg = str(e)
        if 'requests' in error_msg:
            print(f"  ⚠️  Missing dependency: requests (install with: pip install -r requirements.txt)")
            print("  ℹ️  Package structure is correct, but dependencies need to be installed")
        else:
            print(f"  ❌ Failed to import lib modules: {e}")
        return False


def test_integration_imports():
    """Test that integration modules can be imported."""
    print("Testing integration module imports...")
    
    try:
        from integration import RalphOllamaAdapter, call_llm, create_ralph_llm_provider
        print("  ✅ integration package imports work")
        return True
    except ImportError as e:
        error_msg = str(e)
        if 'requests' in error_msg:
            print(f"  ⚠️  Missing dependency: requests (install with: pip install -r requirements.txt)")
            print("  ℹ️  Package structure is correct, but dependencies need to be installed")
        else:
            print(f"  ❌ Failed to import integration modules: {e}")
        return False


def test_optional_imports():
    """Test that optional UI modules can be imported (if installed)."""
    print("Testing optional UI module imports...")
    
    try:
        from ui.app import app
        print("  ✅ UI package imports work (UI dependencies installed)")
        return True
    except ImportError as e:
        print(f"  ⚠️  UI imports failed (expected if UI dependencies not installed): {e}")
        return True  # This is OK - UI is optional


def test_entry_points():
    """Test that entry points are accessible."""
    print("Testing entry points...")
    
    try:
        # Test main functions exist
        from lib.ollama_client import main as ollama_main
        from ui.app import main as ui_main
        print("  ✅ Entry point functions exist")
        return True
    except ImportError as e:
        print(f"  ❌ Entry point functions not found: {e}")
        return False


def test_package_structure():
    """Test that package structure is correct."""
    print("Testing package structure...")
    
    try:
        # Check __init__ files exist and export correctly
        from lib import __all__ as lib_all
        from integration import __all__ as integration_all
        
        expected_lib_exports = ['OllamaClient', 'get_llm_response']
        expected_integration_exports = ['RalphOllamaAdapter', 'create_ralph_llm_provider', 'call_llm']
        
        lib_ok = all(exp in lib_all for exp in expected_lib_exports)
        integration_ok = all(exp in integration_all for exp in expected_integration_exports)
        
        if lib_ok and integration_ok:
            print("  ✅ Package structure is correct")
            return True
        else:
            print(f"  ❌ Package structure issues - lib: {lib_ok}, integration: {integration_ok}")
            return False
    except Exception as e:
        print(f"  ❌ Package structure test failed: {e}")
        return False


def test_config_access():
    """Test that config files can be accessed."""
    print("Testing config file access...")
    
    try:
        from lib.config import get_config_path, get_workflow_config_path
        
        config_path = get_config_path()
        workflow_path = get_workflow_config_path()
        
        # Check if paths are valid (they might be relative)
        print(f"  Config path: {config_path}")
        print(f"  Workflow config path: {workflow_path}")
        print("  ✅ Config path resolution works")
        return True
    except Exception as e:
        print(f"  ❌ Config access failed: {e}")
        return False


def main():
    """Run all package installation tests."""
    print("=" * 70)
    print("Package Installation Tests")
    print("=" * 70)
    print()
    
    results = []
    
    results.append(("Core Imports", test_core_imports()))
    results.append(("Integration Imports", test_integration_imports()))
    results.append(("Optional UI Imports", test_optional_imports()))
    results.append(("Entry Points", test_entry_points()))
    results.append(("Package Structure", test_package_structure()))
    results.append(("Config Access", test_config_access()))
    
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All package installation tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Package may not be installed correctly.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
