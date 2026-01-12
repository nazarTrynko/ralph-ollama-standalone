#!/usr/bin/env python3
"""
Ralph Workflow Demo with Ollama
Demonstrates using Ollama integration with Ralph workflow patterns.
"""

import sys
import json
from pathlib import Path

# Add lib to path
lib_path = Path(__file__).parent.parent / 'lib'
integration_path = Path(__file__).parent.parent / 'integration'
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(integration_path) not in sys.path:
    sys.path.insert(0, str(integration_path))

from ralph_ollama_adapter import call_llm, RalphOllamaAdapter


def read_fix_plan(plan_path='@fix_plan.md'):
    """Read and parse fix plan file."""
    plan_file = Path(plan_path)
    if not plan_file.exists():
        return []
    
    tasks = []
    with open(plan_file) as f:
        lines = f.readlines()
        for line in lines:
            if line.strip().startswith('- [ ]'):
                task = line.strip()[5:].strip()
                tasks.append(task)
    
    return tasks


def generate_solution(prompt, task_type='implementation'):
    """Generate solution using Ollama."""
    try:
        adapter = RalphOllamaAdapter()
        if not adapter.check_available():
            print("⚠️  Ollama server not available")
            return None
        
        result = adapter.generate(
            prompt=prompt,
            task_type=task_type,
            model='llama3.2:latest'  # Use available model
        )
        return result['content']
    except Exception as e:
        print(f"Error generating solution: {e}")
        return None


def demo_basic_usage():
    """Demonstrate basic Ollama usage."""
    print("=" * 60)
    print("Demo 1: Basic Ollama Usage")
    print("=" * 60)
    
    prompt = "Write a Python function to calculate factorial of a number."
    
    print(f"\nPrompt: {prompt}\n")
    print("Generating response...")
    
    response = call_llm(prompt, task_type='implementation')
    
    if response:
        print("\nResponse:")
        print("-" * 60)
        print(response)
        print("-" * 60)
    else:
        print("Failed to generate response")
    
    print()


def demo_task_workflow():
    """Demonstrate Ralph-style task workflow."""
    print("=" * 60)
    print("Demo 2: Ralph Task Workflow")
    print("=" * 60)
    
    # Simulate reading from @fix_plan.md
    print("\nReading tasks from @fix_plan.md...")
    tasks = read_fix_plan()
    
    if not tasks:
        print("No tasks found in @fix_plan.md")
        print("Using example task instead...")
        task = "Implement user authentication"
    else:
        task = tasks[0]
        print(f"Found task: {task}")
    
    # Generate solution
    prompt = f"""
Task: {task}

Requirements:
- Write clean, production-ready code
- Include error handling
- Add docstrings
- Follow best practices
"""
    
    print(f"\nGenerating solution for: {task}")
    print("Generating...")
    
    response = generate_solution(prompt, task_type='implementation')
    
    if response:
        print("\nGenerated Solution:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        print("\n✓ Solution generated successfully")
        print("(In real workflow, this would be written to files and tested)")
    else:
        print("Failed to generate solution")
    
    print()


def demo_different_task_types():
    """Demonstrate different task types."""
    print("=" * 60)
    print("Demo 3: Different Task Types")
    print("=" * 60)
    
    tasks = [
        ("Write unit tests for a function", "testing"),
        ("Document this API endpoint", "documentation"),
        ("Review this code for bugs", "code-review"),
    ]
    
    for prompt, task_type in tasks:
        print(f"\nTask Type: {task_type}")
        print(f"Prompt: {prompt}")
        print("Generating...")
        
        response = call_llm(prompt, task_type=task_type)
        
        if response:
            print(f"Response (first 200 chars): {response[:200]}...")
        else:
            print("Failed")
        print()


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("Ralph Ollama Workflow Demo")
    print("=" * 60)
    print("\nThis demo shows how to use Ollama with Ralph workflow patterns.")
    print()
    
    try:
        # Check if Ollama is available
        adapter = RalphOllamaAdapter()
        if not adapter.check_available():
            print("❌ Error: Ollama server is not running")
            print("   Start it with: ollama serve")
            return 1
        
        print("✓ Ollama server is accessible")
        
        # Run demos
        demo_basic_usage()
        demo_task_workflow()
        demo_different_task_types()
        
        print("=" * 60)
        print("Demo Complete!")
        print("=" * 60)
        print("\nThis demonstrates the integration between Ollama and Ralph workflows.")
        print("You can use these patterns in your own scripts.")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
