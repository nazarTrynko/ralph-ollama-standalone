#!/usr/bin/env python3
"""
Error Handling Examples
Demonstrates how to handle various error types in Ralph Ollama integration.
"""

import sys
from pathlib import Path

from lib.path_utils import setup_paths
setup_paths()

from lib.ollama_client import OllamaClient
from lib.exceptions import (
    OllamaConnectionError,
    OllamaModelError,
    OllamaConfigError,
    OllamaServerError,
    OllamaTimeoutError,
)


def example_connection_error():
    """Example: Handling connection errors."""
    print("=" * 60)
    print("Example 1: Handling Connection Errors")
    print("=" * 60)
    
    try:
        client = OllamaClient()
        result = client.generate("Hello")
        print(f"Response: {result['response']}")
    except OllamaConnectionError as e:
        print(f"❌ Connection Error: {e}")
        print(f"   Server URL: {e.server_url}")
        print("   💡 Solution: Start Ollama server with 'ollama serve'")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def example_model_error():
    """Example: Handling model errors."""
    print("\n" + "=" * 60)
    print("Example 2: Handling Model Errors")
    print("=" * 60)
    
    try:
        client = OllamaClient()
        result = client.generate("Hello", model="nonexistent-model")
        print(f"Response: {result['response']}")
    except OllamaModelError as e:
        print(f"❌ Model Error: {e}")
        print(f"   Model: {e.model}")
        if e.available_models:
            print(f"   Available models: {', '.join(e.available_models)}")
        print("   💡 Solution: Pull the model with 'ollama pull <model-name>'")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def example_config_error():
    """Example: Handling configuration errors."""
    print("\n" + "=" * 60)
    print("Example 3: Handling Configuration Errors")
    print("=" * 60)
    
    try:
        # Try to use non-existent config file
        client = OllamaClient("/nonexistent/config.json")
    except OllamaConfigError as e:
        print(f"❌ Config Error: {e}")
        print(f"   Config Path: {e.config_path}")
        print("   💡 Solution: Create config file or set RALPH_OLLAMA_CONFIG environment variable")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def example_timeout_error():
    """Example: Handling timeout errors."""
    print("\n" + "=" * 60)
    print("Example 4: Handling Timeout Errors")
    print("=" * 60)
    
    try:
        client = OllamaClient()
        # This might timeout if server is slow
        result = client.generate("Hello" * 1000)  # Very long prompt
        print(f"Response: {result['response']}")
    except OllamaTimeoutError as e:
        print(f"❌ Timeout Error: {e}")
        print(f"   Timeout: {e.timeout}s")
        print("   💡 Solution: Increase timeout in config or check server performance")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def example_server_error():
    """Example: Handling server errors."""
    print("\n" + "=" * 60)
    print("Example 5: Handling Server Errors")
    print("=" * 60)
    
    try:
        client = OllamaClient()
        result = client.list_models()
        print(f"Models: {', '.join(result)}")
    except OllamaServerError as e:
        print(f"❌ Server Error: {e}")
        print(f"   Server URL: {e.server_url}")
        print(f"   Status Code: {e.status_code}")
        print("   💡 Solution: Check Ollama server logs and status")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def example_graceful_degradation():
    """Example: Graceful degradation pattern."""
    print("\n" + "=" * 60)
    print("Example 6: Graceful Degradation Pattern")
    print("=" * 60)
    
    client = OllamaClient()
    
    # Check server before attempting operation
    if not client.check_server():
        print("⚠️  Ollama server is not running")
        print("   Falling back to alternative method...")
        # In real code, you might fall back to cloud API
        return
    
    # Check if model exists
    try:
        models = client.list_models()
        if "llama3.2" not in models:
            print("⚠️  Model 'llama3.2' not found")
            print(f"   Available models: {', '.join(models)}")
            print("   Using first available model...")
            model = models[0] if models else None
        else:
            model = "llama3.2"
        
        if model:
            result = client.generate("Hello", model=model)
            print(f"✅ Success: {result['response']}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all error handling examples."""
    print("Ralph Ollama - Error Handling Examples")
    print("=" * 60)
    print()
    
    # Note: Some examples may fail if Ollama is not running
    # This is expected and demonstrates error handling
    
    example_connection_error()
    example_model_error()
    example_config_error()
    example_timeout_error()
    example_server_error()
    example_graceful_degradation()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
