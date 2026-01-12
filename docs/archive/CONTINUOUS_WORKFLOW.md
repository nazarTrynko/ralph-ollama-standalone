# Running Ollama Continuously with Ralph on a Local Folder

Complete guide for setting up continuous Ralph workflows with Ollama on a local folder.

---

## Overview

This guide shows you how to:

1. Start Ollama server (runs continuously)
2. Run Ralph continuously on a local folder
3. Monitor and manage the workflow

---

## Step 1: Start Ollama Server (Continuous)

The Ollama server needs to run continuously in the background.

### Option A: Run in Terminal (Recommended for Development)

```bash
# Start Ollama server (keep this terminal open)
ollama serve
```

**Note:** Keep this terminal window open. The server will run until you stop it (Ctrl+C).

### Option B: Run as Background Service (Production)

**macOS (using launchd):**

```bash
# Create a launchd service (runs automatically on boot)
# See: https://ollama.ai/docs/installation#macos
```

**Linux (using systemd):**

```bash
# Create systemd service
sudo systemctl enable ollama
sudo systemctl start ollama
```

### Verify Ollama is Running

```bash
# Check if server is accessible
curl http://localhost:11434/api/tags

# Should return JSON with available models
```

---

## Step 2: Pull Required Models

Before running Ralph, make sure you have the models you need:

```bash
# Pull recommended models
ollama pull llama3.2      # General purpose
ollama pull codellama     # Code generation

# Verify models are available
ollama list
```

---

## Step 3: Set Up Your Local Folder

Navigate to the folder you want Ralph to work on:

```bash
# Navigate to your project folder
cd /path/to/your/project

# Or if working in the ralph-ollama-standalone folder
cd /Users/nazartrynko/ralph-ollama-standalone
```

---

## Step 4: Activate Virtual Environment

```bash
# Activate the virtual environment
source venv/bin/activate

# Or use the activation script
source activate-venv.sh
```

---

## Step 5: Run Ralph Continuously

You have several options for running Ralph continuously:

### Option 1: Continuous Code Improvement (Recommended)

This script continuously analyzes and improves code in your folder:

```bash
# Run continuously, checking every 5 minutes (300 seconds)
python3 scripts/improve-code.py --interval 300

# Run continuously with specific model
python3 scripts/improve-code.py --model codellama --interval 300

# Run continuously, process max 10 files per cycle
python3 scripts/improve-code.py --interval 300 --max-files 10
```

**What it does:**

- Scans Python files in your folder
- Analyzes code quality using Ollama
- Suggests and applies improvements
- Runs continuously at specified intervals
- Press Ctrl+C to stop

### Option 2: One-Time Run (Test First)

Before running continuously, test with a one-time run:

```bash
# Run once, improve up to 5 files
python3 scripts/improve-code.py --once --max-files 5

# Run once with specific model
python3 scripts/improve-code.py --once --model llama3.2 --max-files 5
```

### Option 3: Custom Continuous Workflow

Create your own continuous workflow script:

```python
#!/usr/bin/env python3
"""Custom continuous Ralph workflow"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from integration.ralph_ollama_adapter import call_llm, RalphOllamaAdapter

def process_folder(folder_path: Path, interval: int = 300):
    """Continuously process tasks in a folder."""
    adapter = RalphOllamaAdapter()

    if not adapter.check_available():
        print("❌ Ollama server not available")
        return

    print(f"🚀 Starting continuous workflow on: {folder_path}")
    print(f"⏱️  Interval: {interval} seconds")
    print("Press Ctrl+C to stop\n")

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"Cycle #{cycle} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")

            # Read tasks from @fix_plan.md if it exists
            plan_file = folder_path / '@fix_plan.md'
            if plan_file.exists():
                tasks = read_tasks(plan_file)
                if tasks:
                    task = tasks[0]
                    print(f"📋 Processing task: {task}")

                    # Generate solution
                    solution = call_llm(
                        f"Implement: {task}",
                        task_type="implementation"
                    )

                    if solution:
                        print(f"✅ Generated solution (length: {len(solution)} chars)")
                        # Your logic to apply solution here
                    else:
                        print("⚠️  Failed to generate solution")
                else:
                    print("✅ No tasks remaining")
            else:
                print("ℹ️  No @fix_plan.md found")

            print(f"\n⏳ Waiting {interval} seconds until next cycle...")
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\n🛑 Stopped by user")
        print(f"Total cycles: {cycle}")

def read_tasks(plan_file: Path):
    """Read tasks from @fix_plan.md."""
    tasks = []
    with open(plan_file) as f:
        for line in f:
            if line.strip().startswith('- [ ]'):
                task = line.strip()[5:].strip()
                tasks.append(task)
    return tasks

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', type=str, default='.',
                       help='Folder to process')
    parser.add_argument('--interval', type=int, default=300,
                       help='Seconds between cycles')
    args = parser.parse_args()

    process_folder(Path(args.folder), args.interval)
```

Save as `scripts/continuous-ralph.py` and run:

```bash
python3 scripts/continuous-ralph.py --folder /path/to/your/project --interval 300
```

---

## Step 6: Set Environment Variables (Optional)

For advanced usage, set environment variables:

```bash
export RALPH_LLM_PROVIDER=ollama
export RALPH_LLM_MODEL=llama3.2:latest
export RALPH_OLLAMA_CONFIG=./config/ollama-config.json
export RALPH_WORKFLOW_CONFIG=./config/workflow-config.json
```

Then use in your scripts:

```python
import os
from integration.ralph_ollama_adapter import call_llm

# Environment variables are automatically used
response = call_llm("Your prompt", task_type="implementation")
```

---

## Complete Setup Example

Here's a complete example of running everything:

### Terminal 1: Ollama Server

```bash
# Start Ollama server (keep running)
ollama serve
```

### Terminal 2: Ralph Continuous Workflow

```bash
# Navigate to your project
cd /path/to/your/project

# Activate virtual environment
source venv/bin/activate

# Run continuous code improvement
python3 scripts/improve-code.py --interval 300 --max-files 10
```

### Terminal 3: Monitor (Optional)

```bash
# Watch for changes
watch -n 5 'ls -la state/improvements.json 2>/dev/null || echo "No improvements yet"'

# Or monitor Ollama
watch -n 5 'curl -s http://localhost:11434/api/tags | jq'
```

---

## Configuration

### Adjust Improvement Interval

```bash
# Check every 5 minutes (300 seconds)
python3 scripts/improve-code.py --interval 300

# Check every 10 minutes (600 seconds)
python3 scripts/improve-code.py --interval 600

# Check every minute (60 seconds) - for testing
python3 scripts/improve-code.py --interval 60
```

### Limit Files Processed

```bash
# Process max 5 files per cycle
python3 scripts/improve-code.py --max-files 5

# Process max 20 files per cycle
python3 scripts/improve-code.py --max-files 20

# Process all files (no limit)
python3 scripts/improve-code.py
```

### Use Specific Model

```bash
# Use codellama for code tasks
python3 scripts/improve-code.py --model codellama

# Use llama3.2 for general tasks
python3 scripts/improve-code.py --model llama3.2
```

---

## Working with Specific Folders

### Process a Different Folder

```bash
# Navigate to the folder first
cd /path/to/your/project

# Then run Ralph
python3 /path/to/ralph-ollama-standalone/scripts/improve-code.py --interval 300
```

### Process Multiple Folders

Create a wrapper script:

```bash
#!/bin/bash
# process-multiple-folders.sh

FOLDERS=(
    "/path/to/project1"
    "/path/to/project2"
    "/path/to/project3"
)

for folder in "${FOLDERS[@]}"; do
    echo "Processing: $folder"
    cd "$folder"
    python3 /path/to/ralph-ollama-standalone/scripts/improve-code.py --once --max-files 5
done
```

---

## Monitoring and Logs

### View Improvement History

```bash
# View improvement log
cat state/improvements.json | jq

# View recent improvements
cat state/improvements.json | jq '.improvements[-5:]'
```

### Check Ollama Status

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# List available models
ollama list

# Check model info
ollama show llama3.2
```

---

## Troubleshooting

### Ollama Server Not Running

```bash
# Start Ollama
ollama serve

# Check if it's running
curl http://localhost:11434/api/tags
```

### Model Not Found

```bash
# List available models
ollama list

# Pull missing model
ollama pull llama3.2
```

### Virtual Environment Issues

```bash
# Recreate virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Import Errors

```bash
# Make sure you're in the project root
cd /Users/nazartrynko/ralph-ollama-standalone

# Activate virtual environment
source venv/bin/activate

# Verify imports
python3 -c "from integration.ralph_ollama_adapter import call_llm; print('OK')"
```

---

## Best Practices

1. **Start with One-Time Run**: Test with `--once` before running continuously
2. **Limit Files Initially**: Use `--max-files 5` to start small
3. **Monitor First Cycle**: Watch the first cycle to ensure it's working
4. **Use Appropriate Interval**: 300 seconds (5 minutes) is a good default
5. **Keep Ollama Running**: Make sure Ollama server stays running
6. **Check Logs**: Review `state/improvements.json` regularly
7. **Backup Before Running**: Make sure your code is committed/backed up

---

## Quick Reference

```bash
# 1. Start Ollama (Terminal 1)
ollama serve

# 2. Activate environment (Terminal 2)
cd /path/to/your/project
source venv/bin/activate

# 3. Run continuously (Terminal 2)
python3 scripts/improve-code.py --interval 300

# 4. Stop with Ctrl+C
```

---

## Next Steps

- See [USAGE.md](USAGE.md) for more usage patterns
- See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
- See [docs/INTEGRATION.md](docs/INTEGRATION.md) for advanced integration

---

**Last Updated:** 2025-01-12
