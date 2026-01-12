#!/usr/bin/env python3
"""
Test script for Ollama connection and basic functionality.
"""

import sys
from pathlib import Path

# Add project root to path to enable package imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from lib.ollama_client import OllamaClient


def test_server_connection():
    """Test if Ollama server is accessible."""
    print("Testing Ollama server connection...")
    client = OllamaClient()
    
    if client.check_server():
        print("✓ Ollama server is running")
        return True
    else:
        print("✗ Ollama server is not running")
        print("  Start with: ollama serve")
        return False


def test_list_models():
    """Test listing available models."""
    print("\nTesting model listing...")
    client = OllamaClient()
    
    try:
        models = client.list_models()
        if models:
            print(f"✓ Found {len(models)} models:")
            for model in models:
                print(f"  - {model}")
            return True
        else:
            print("✗ No models found")
            print("  Pull a model with: ollama pull llama3.2")
            return False
    except Exception as e:
        print(f"✗ Failed to list models: {e}")
        return False


def test_model_generation(model: str = None):
    """Test model generation."""
    print(f"\nTesting model generation ({model or 'default'})...")
    client = OllamaClient()
    
    if model is None:
        model = client.default_model
    
    try:
        result = client.generate(
            prompt="Say hello in exactly one word.",
            model=model
        )
        
        response = result['response'].strip()
        print(f"✓ Model '{model}' responded: {response}")
        
        if result.get('tokens'):
            tokens = result['tokens']
            print(f"  Tokens: {tokens.get('total', 0)} total "
                  f"({tokens.get('prompt', 0)} prompt + {tokens.get('completion', 0)} completion)")
        
        return True
    except Exception as e:
        print(f"✗ Failed to generate response: {e}")
        return False


def test_config_loading():
    """Test configuration loading."""
    print("\nTesting configuration loading...")
    
    try:
        client = OllamaClient()
        print(f"✓ Config loaded from: {client.config_path}")
        print(f"  Server: {client.base_url}")
        print(f"  Default model: {client.default_model}")
        return True
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False


def main():
    """Run all tests."""
    print("Ollama Connection Test")
    print("=" * 50)
    
    results = []
    
    # Test config
    results.append(("Config Loading", test_config_loading()))
    
    # Test server
    if results[-1][1]:  # Only continue if config loaded
        results.append(("Server Connection", test_server_connection()))
        
        if results[-1][1]:  # Only continue if server running
            results.append(("List Models", test_list_models()))
            
            # Test generation with default model
            client = OllamaClient()
            model = client.default_model if client.check_server() else None
            if model:
                results.append(("Model Generation", test_model_generation(model)))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed. Check output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
