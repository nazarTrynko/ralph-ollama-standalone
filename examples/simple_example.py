#!/usr/bin/env python3
"""
Simple example of using OllamaClient with Ralph workflow.
"""

import sys
from pathlib import Path

from lib.path_utils import setup_paths
setup_paths()

from lib.ollama_client import OllamaClient, get_llm_response


def example_basic_usage():
    """Basic usage example."""
    print("Example 1: Basic Usage")
    print("-" * 50)
    
    # Initialize client
    client = OllamaClient()
    
    # Generate response
    result = client.generate(
        prompt="Write a Python function to calculate fibonacci numbers.",
        model="codellama"  # Or use default
    )
    
    print(f"Response:\n{result['response']}\n")
    print(f"Tokens used: {result['tokens']['total']}\n")


def example_with_system_prompt():
    """Example with system prompt."""
    print("Example 2: With System Prompt")
    print("-" * 50)
    
    system_prompt = """You are a helpful coding assistant. 
Write clean, well-documented code following best practices."""
    
    client = OllamaClient()
    result = client.generate(
        prompt="Create a function to validate email addresses.",
        system_prompt=system_prompt,
        model="codellama"
    )
    
    print(f"Response:\n{result['response']}\n")


def example_convenience_function():
    """Example using convenience function."""
    print("Example 3: Convenience Function")
    print("-" * 50)
    
    # Simple one-liner
    response = get_llm_response(
        prompt="Explain recursion in one sentence.",
        model="llama3.2"
    )
    
    print(f"Response: {response}\n")


def example_check_models():
    """Example of checking available models."""
    print("Example 4: List Available Models")
    print("-" * 50)
    
    client = OllamaClient()
    
    if client.check_server():
        models = client.list_models()
        print(f"Available models: {', '.join(models)}\n")
    else:
        print("Server not running\n")


def example_ralph_workflow_style():
    """Example simulating Ralph workflow style."""
    print("Example 5: Ralph Workflow Style")
    print("-" * 50)
    
    # Simulate a task from Ralph workflow
    task_prompt = """
Task: Implement a function to calculate factorial.

Requirements:
- Function name: factorial
- Parameter: n (integer)
- Return: integer
- Handle edge cases (n=0, n<0)
- Include docstring
"""
    
    system_prompt = """
You are Ralph, an autonomous AI development agent.
Write clean, production-ready code with proper error handling and documentation.
"""
    
    client = OllamaClient()
    result = client.generate(
        prompt=task_prompt,
        system_prompt=system_prompt,
        model="codellama"
    )
    
    print("Generated code:")
    print(result['response'])
    print(f"\nTokens: {result['tokens']['total']}\n")


def main():
    """Run examples."""
    print("Ollama Client Examples")
    print("=" * 50)
    print()
    
    try:
        # Check server first
        client = OllamaClient()
        if not client.check_server():
            print("Error: Ollama server is not running.")
            print("Start with: ollama serve")
            return 1
        
        # Run examples
        example_check_models()
        example_basic_usage()
        example_with_system_prompt()
        example_convenience_function()
        example_ralph_workflow_style()
        
        print("=" * 50)
        print("Examples completed!")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
