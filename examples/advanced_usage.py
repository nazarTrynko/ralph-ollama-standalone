#!/usr/bin/env python3
"""
Advanced Usage Examples
Demonstrates advanced patterns and use cases for Ralph Ollama integration.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

from lib.path_utils import setup_paths
setup_paths()

from lib.ollama_client import OllamaClient
from integration.ralph_ollama_adapter import RalphOllamaAdapter, create_ralph_llm_provider


def example_batch_processing():
    """Example: Processing multiple prompts in batch."""
    print("=" * 60)
    print("Example 1: Batch Processing")
    print("=" * 60)
    
    client = OllamaClient()
    
    prompts = [
        "Write a Python function to calculate factorial",
        "Write a Python function to check if a number is prime",
        "Write a Python function to reverse a string",
    ]
    
    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\nProcessing prompt {i}/{len(prompts)}...")
        try:
            result = client.generate(prompt, model="codellama")
            results.append({
                'prompt': prompt,
                'response': result['response'],
                'tokens': result['tokens']['total']
            })
            print(f"✅ Generated {result['tokens']['total']} tokens")
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({'prompt': prompt, 'error': str(e)})
    
    print(f"\n✅ Processed {len(results)} prompts")
    total_tokens = sum(r.get('tokens', 0) for r in results)
    print(f"   Total tokens: {total_tokens}")


def example_task_based_selection():
    """Example: Using task-based model selection."""
    print("\n" + "=" * 60)
    print("Example 2: Task-Based Model Selection")
    print("=" * 60)
    
    adapter = RalphOllamaAdapter()
    
    tasks = [
        ("Implement a binary search function", "implementation"),
        ("Write unit tests for the binary search function", "testing"),
        ("Document the binary search function", "documentation"),
        ("Review this code for bugs", "code-review"),
    ]
    
    for prompt, task_type in tasks:
        print(f"\nTask: {task_type}")
        print(f"Prompt: {prompt[:50]}...")
        try:
            result = adapter.generate(prompt, task_type=task_type)
            print(f"✅ Model: {result['model']}")
            print(f"   Response length: {len(result['content'])} chars")
        except Exception as e:
            print(f"❌ Error: {e}")


def example_custom_parameters():
    """Example: Using custom generation parameters."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Generation Parameters")
    print("=" * 60)
    
    client = OllamaClient()
    
    prompt = "Write a creative story about a robot"
    
    # Low temperature (more deterministic)
    print("\nLow temperature (0.3):")
    result = client.generate(prompt, temperature=0.3, num_predict=100)
    print(f"Response: {result['response'][:100]}...")
    
    # High temperature (more creative)
    print("\nHigh temperature (1.0):")
    result = client.generate(prompt, temperature=1.0, num_predict=100)
    print(f"Response: {result['response'][:100]}...")
    
    # Custom top_p
    print("\nCustom top_p (0.95):")
    result = client.generate(prompt, top_p=0.95, num_predict=100)
    print(f"Response: {result['response'][:100]}...")


def example_provider_factory():
    """Example: Using provider factory pattern."""
    print("\n" + "=" * 60)
    print("Example 4: Provider Factory Pattern")
    print("=" * 60)
    
    # This automatically selects Ollama if configured
    provider = create_ralph_llm_provider()
    
    if provider:
        print("✅ Ollama provider created")
        print(f"   Default model: {provider.get_default_model()}")
        print(f"   Available: {provider.check_available()}")
        
        if provider.check_available():
            result = provider.generate("Hello", task_type="implementation")
            print(f"✅ Generated response: {result['content'][:50]}...")
    else:
        print("⚠️  Ollama provider not available")
        print("   Set RALPH_LLM_PROVIDER=ollama to enable")


def example_error_recovery():
    """Example: Error recovery with fallback."""
    print("\n" + "=" * 60)
    print("Example 5: Error Recovery with Fallback")
    print("=" * 60)
    
    client = OllamaClient()
    
    # Try preferred model first
    preferred_models = ["codellama", "llama3.2", "phi3"]
    
    prompt = "Write a Python function"
    result = None
    
    for model in preferred_models:
        try:
            print(f"\nTrying model: {model}")
            result = client.generate(prompt, model=model)
            print(f"✅ Success with {model}")
            break
        except Exception as e:
            print(f"❌ Failed with {model}: {e}")
            continue
    
    if result:
        print(f"\n✅ Final response: {result['response'][:100]}...")
    else:
        print("\n❌ All models failed")


def example_monitoring():
    """Example: Monitoring token usage and performance."""
    print("\n" + "=" * 60)
    print("Example 6: Monitoring Usage")
    print("=" * 60)
    
    client = OllamaClient()
    
    prompts = [
        "Short prompt",
        "This is a medium length prompt that requires more tokens",
        "This is a very long prompt that will require significantly more tokens to process and generate a response",
    ]
    
    total_tokens = 0
    for prompt in prompts:
        try:
            result = client.generate(prompt)
            tokens = result['tokens']
            total_tokens += tokens['total']
            
            print(f"\nPrompt: {prompt[:30]}...")
            print(f"  Prompt tokens: {tokens['prompt']}")
            print(f"  Completion tokens: {tokens['completion']}")
            print(f"  Total tokens: {tokens['total']}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n📊 Total tokens used: {total_tokens}")


def main():
    """Run all advanced examples."""
    print("Ralph Ollama - Advanced Usage Examples")
    print("=" * 60)
    print()
    
    # Note: These examples require Ollama server to be running
    # Some may fail gracefully, demonstrating error handling
    
    try:
        example_batch_processing()
        example_task_based_selection()
        example_custom_parameters()
        example_provider_factory()
        example_error_recovery()
        example_monitoring()
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        print("   Make sure Ollama server is running")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
