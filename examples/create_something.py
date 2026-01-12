#!/usr/bin/env python3
"""
Create Something with Ralph Ollama
Demonstrates using Ollama to generate code, tests, and documentation.
"""

import sys
from pathlib import Path

# Add project root to path to enable package imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from integration.ralph_ollama_adapter import call_llm, RalphOllamaAdapter


def create_function():
    """Create a Python function using Ollama."""
    print("=" * 60)
    print("Creating a Python Function")
    print("=" * 60)
    
    prompt = """
Write a Python function called `fibonacci_sequence` that:
- Takes an integer n as parameter
- Returns a list of the first n Fibonacci numbers
- Includes proper docstring
- Has error handling for invalid inputs
- Uses efficient algorithm
"""
    
    print("\nPrompt:", prompt.strip())
    print("\nGenerating with Ollama...\n")
    
    result = call_llm(prompt, task_type='implementation')
    
    print("=" * 60)
    print("Generated Code:")
    print("=" * 60)
    print(result if isinstance(result, str) else result.get('content', result))
    print("=" * 60)
    
    return result


def create_tests():
    """Create unit tests using Ollama."""
    print("\n" + "=" * 60)
    print("Creating Unit Tests")
    print("=" * 60)
    
    function_code = """
def fibonacci_sequence(n):
    \"\"\"Generate first n Fibonacci numbers.\"\"\"
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return []
    if n == 1:
        return [0]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib
"""
    
    prompt = f"""
Write comprehensive unit tests for this function using pytest:

{function_code}

Include tests for:
- Normal cases
- Edge cases (n=0, n=1, n=2)
- Error handling
- Large values
"""
    
    print("\nGenerating tests...\n")
    
    result = call_llm(prompt, task_type='testing')
    
    print("=" * 60)
    print("Generated Tests:")
    print("=" * 60)
    print(result if isinstance(result, str) else result.get('content', result))
    print("=" * 60)
    
    return result


def create_documentation():
    """Create documentation using Ollama."""
    print("\n" + "=" * 60)
    print("Creating Documentation")
    print("=" * 60)
    
    prompt = """
Write clear documentation for a REST API endpoint:

POST /api/users
- Creates a new user
- Accepts JSON: {"name": string, "email": string, "age": integer}
- Returns: {"id": integer, "name": string, "email": string, "created_at": timestamp}

Include:
- Description
- Request format
- Response format
- Error codes
- Example request/response
"""
    
    print("\nGenerating documentation...\n")
    
    result = call_llm(prompt, task_type='documentation')
    
    print("=" * 60)
    print("Generated Documentation:")
    print("=" * 60)
    print(result if isinstance(result, str) else result.get('content', result))
    print("=" * 60)
    
    return result


def main():
    """Main function."""
    print("\n" + "=" * 60)
    print("Ralph Ollama - Create Something Demo")
    print("=" * 60)
    print("\nThis script uses local Ollama to generate:")
    print("1. A Python function")
    print("2. Unit tests for the function")
    print("3. API documentation")
    print()
    
    try:
        # Check if Ollama is available
        adapter = RalphOllamaAdapter()
        if not adapter.check_available():
            print("❌ Error: Ollama server is not running")
            print("   Start it with: ollama serve")
            return 1
        
        print("✓ Ollama server is accessible\n")
        
        # Create function
        function = create_function()
        
        # Create tests
        tests = create_tests()
        
        # Create documentation
        docs = create_documentation()
        
        print("\n" + "=" * 60)
        print("✅ All Generated Content Created!")
        print("=" * 60)
        print("\nGenerated:")
        print("  - Python function (Fibonacci sequence)")
        print("  - Unit tests (pytest format)")
        print("  - API documentation (REST endpoint)")
        print("\nAll content was generated using local Ollama models!")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
