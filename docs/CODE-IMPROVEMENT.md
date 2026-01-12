# Continuous Code Improvement

Automatically improve your codebase using Ollama AI analysis.

## Overview

The code improvement script analyzes your Python code and suggests specific improvements including:
- Bug fixes
- Code refactoring
- Performance optimizations
- Style improvements
- Documentation enhancements

## Quick Start

### Run Once

```bash
# Improve up to 5 files
python3 scripts/improve-code.py --once --max-files 5

# Or use the convenience script
./scripts/improve-code.sh --once --max-files 5
```

### Run Continuously

```bash
# Run continuously, checking every 5 minutes
python3 scripts/improve-code.py

# Custom interval (every 10 minutes)
python3 scripts/improve-code.py --interval 600
```

## Usage

### Basic Usage

```bash
# Run once, process all files
python3 scripts/improve-code.py --once

# Run continuously (default: every 5 minutes)
python3 scripts/improve-code.py
```

### Options

- `--once`: Run once instead of continuously
- `--interval SECONDS`: Time between cycles (default: 300)
- `--model MODEL_NAME`: Use specific Ollama model (default: auto-select)
- `--max-files N`: Process maximum N files per cycle

### Examples

```bash
# Quick test: improve 3 files once
python3 scripts/improve-code.py --once --max-files 3

# Use codellama for code improvements
python3 scripts/improve-code.py --model codellama --once

# Run every hour
python3 scripts/improve-code.py --interval 3600

# Continuous improvement with limit
python3 scripts/improve-code.py --max-files 10
```

## How It Works

1. **Scans** all Python files in the project
2. **Analyzes** each file using Ollama AI
3. **Suggests** specific improvements with code examples
4. **Applies** improvements (with confirmation in interactive mode)
5. **Logs** all improvements to `state/improvements.json`

## Safety Features

- ✅ **Skips recently improved files** (within last hour)
- ✅ **Asks for confirmation** before applying changes (interactive mode)
- ✅ **Tracks all improvements** in a log file
- ✅ **Skips large files** (>50KB) to avoid timeouts
- ✅ **Only suggests safe improvements** that won't break functionality

## Improvement Log

All improvements are logged to `state/improvements.json`:

```json
{
  "improvements": [
    {
      "file": "lib/ollama_client.py",
      "timestamp": "2024-01-12T10:30:00",
      "improvements_applied": 2,
      "score_before": 75,
      "summary": "Improved error handling and added type hints"
    }
  ],
  "last_run": "2024-01-12T10:30:00"
}
```

## What Gets Improved

The AI analyzes code for:

1. **Bug Fixes**: Logic errors, edge cases, exception handling
2. **Refactoring**: Code duplication, complexity, structure
3. **Optimization**: Performance bottlenecks, inefficient patterns
4. **Style**: PEP 8 compliance, naming conventions, formatting
5. **Documentation**: Missing docstrings, unclear comments

## Excluded Files/Directories

The script automatically excludes:
- `.git/` - Git metadata
- `__pycache__/` - Python cache
- `venv/` - Virtual environments
- `node_modules/` - Node.js dependencies
- `.cursor/` - Cursor IDE files
- `state/` - State/log files

## Requirements

- Ollama server running (`ollama serve`)
- At least one model pulled (e.g., `ollama pull codellama`)
- Python dependencies installed (`pip install -r requirements.txt`)

## Tips

1. **Start Small**: Use `--max-files 3` first to see how it works
2. **Review Changes**: Check git diff after improvements
3. **Test After**: Run your tests after improvements are applied
4. **Use Specific Models**: `codellama` is great for code improvements
5. **Adjust Interval**: Longer intervals (1 hour+) for less frequent checks

## Troubleshooting

### "Ollama server is not running"

```bash
# Start Ollama
ollama serve
```

### "No improvements suggested"

- Code might already be good
- File might have been recently improved
- Try a different model: `--model codellama`

### "Too many files"

Use `--max-files` to limit:
```bash
python3 scripts/improve-code.py --once --max-files 5
```

### Improvements seem wrong

- Review the improvement log
- Check git diff before committing
- The script asks for confirmation in interactive mode

## Integration with Git

After improvements, review and commit:

```bash
# Review changes
git diff

# Stage improvements
git add .

# Commit
git commit -m "Code improvements via Ollama AI"
```

## Continuous Improvement Workflow

1. Start the improvement script in background:
   ```bash
   nohup python3 scripts/improve-code.py --interval 600 > improve.log 2>&1 &
   ```

2. Review improvements periodically:
   ```bash
   git status
   git diff
   ```

3. Test and commit:
   ```bash
   python3 tests/test_connection.py
   git commit -am "Auto-improvements"
   ```

---

**Note**: Always review AI-suggested improvements before committing. The script is designed to be safe, but human review is recommended.
