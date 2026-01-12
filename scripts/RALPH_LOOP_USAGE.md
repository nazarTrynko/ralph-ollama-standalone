# Ralph Loop Script - Usage Guide

## Overview

The Ralph Loop script (`ralph-loop.sh` / `ralph-loop.py`) allows you to run Ralph autonomous development loops with cycle control and prompt input. It executes tasks from `@fix_plan.md` in phases (Study → Implement → Test → Update) with configurable min/max cycle limits.

## Quick Start

```bash
# Basic usage - create a new project
./scripts/ralph-loop.sh --prompt "Create a simple calculator app" --min-cycles 4 --max-cycles 12
```

## Command-Line Arguments

| Argument                    | Short   | Required | Default    | Description                                                                                                                |
| --------------------------- | ------- | -------- | ---------- | -------------------------------------------------------------------------------------------------------------------------- |
| `--prompt`                  | `-p`    | ✅ Yes   | -          | Prompt/command used as task description and context                                                                        |
| `--min-cycles`              | `--min` | No       | `4`        | Minimum number of phases to execute (4 = one full task)                                                                    |
| `--max-cycles`              | `--max` | No       | `40`       | Maximum number of phases to execute (40 = ~10 tasks)                                                                       |
| `--project-path`            | -       | No       | Auto       | Path to project directory (default: creates in `projects/`). Special values: `.`, `root`, `ROOT` to work on root directory |
| `--project-name`            | -       | No       | Auto       | Project name (default: generated from prompt)                                                                              |
| `--model`                   | -       | No       | Config     | Ollama model to use (e.g., `llama3.2`, `codellama`)                                                                        |
| `--mode`                    | -       | No       | `non_stop` | Loop mode: `phase_by_phase` or `non_stop`                                                                                  |
| `--verbose`                 | `-v`    | No       | -          | Enable verbose output                                                                                                      |
| `--root` / `--work-on-root` | -       | No       | -          | Work on root directory (ralph-ollama-standalone project itself) instead of `projects/` folder. Shows confirmation prompt.  |

## Usage Examples

### Example 1: Create a New Project

Create a new project with a simple prompt and run 1-3 tasks:

```bash
./scripts/ralph-loop.sh \
  --prompt "Create a Python CLI tool for managing todo lists" \
  --min-cycles 4 \
  --max-cycles 12
```

**What happens:**

- Creates new project in `projects/` directory
- Uses prompt as project description
- Adds prompt as initial task in `@fix_plan.md`
- Runs until 12 phases completed (or tasks finish)
- Each task = 4 phases (Study, Implement, Test, Update)

### Example 2: Continue Existing Project

Add a new task to an existing project:

```bash
./scripts/ralph-loop.sh \
  --prompt "Add error handling and input validation" \
  --project-path projects/Video_ideas \
  --min-cycles 8 \
  --max-cycles 20
```

**What happens:**

- Uses existing project at `projects/Video_ideas`
- Adds prompt as new task if no tasks exist
- Runs 2-5 tasks (8-20 phases)
- Continues from existing `@fix_plan.md`

### Example 3: Use Specific Model

Run with a code-focused model for implementation tasks:

```bash
./scripts/ralph-loop.sh \
  --prompt "Implement user authentication with JWT tokens" \
  --model codellama \
  --min-cycles 4 \
  --max-cycles 16
```

**What happens:**

- Uses `codellama` model (better for code generation)
- Runs 1-4 tasks
- Model selection overrides config defaults

### Example 4: Work on Root Directory

Work directly on the ralph-ollama-standalone project itself (with confirmation):

```bash
./scripts/ralph-loop.sh \
  --prompt "Add new feature to core engine" \
  --root \
  --min-cycles 4 \
  --max-cycles 8
```

**What happens:**

- Shows confirmation prompt before proceeding
- Works on root directory instead of `projects/` folder
- Modifies files in the main project directory
- Uses existing `@fix_plan.md` from root if it exists

**Alternative using special path:**

```bash
./scripts/ralph-loop.sh \
  --prompt "Refactor code structure" \
  --project-path . \
  --min-cycles 4 \
  --max-cycles 8
```

**Note:** Both `--root` flag and `--project-path .` (or `root`, `ROOT`) will work on the root directory. A confirmation prompt will be shown for safety.

### Example 5: Phase-by-Phase Mode

Run in interactive mode (pauses after each phase):

```bash
./scripts/ralph-loop.sh \
  --prompt "Refactor database queries to use connection pooling" \
  --mode phase_by_phase \
  --min-cycles 4 \
  --max-cycles 8
```

**What happens:**

- Pauses after each phase (Study, Implement, Test, Update)
- Allows review before continuing
- Useful for debugging or careful review

### Example 6: Verbose Output

Get detailed progress information:

```bash
./scripts/ralph-loop.sh \
  --prompt "Create REST API endpoints for user management" \
  --verbose \
  --min-cycles 4 \
  --max-cycles 12
```

**What happens:**

- Shows detailed phase progress percentages
- Displays current task being processed
- Provides more status information

## Understanding Cycles

**One Cycle = One Phase Execution**

- **Study Phase**: Analyzes task requirements
- **Implement Phase**: Creates/modifies code files
- **Test Phase**: Validates implementation
- **Update Phase**: Marks task complete in `@fix_plan.md`

**One Task = 4 Cycles** (one of each phase)

### Cycle Limits

- **`--min-cycles`**: Minimum phases to execute before stopping (soft limit)
  - If tasks finish early but min not met, waits for more tasks
  - Default: `4` (one full task)
- **`--max-cycles`**: Maximum phases to execute (hard limit)
  - Stops immediately when reached
  - Default: `40` (approximately 10 tasks)

### Examples

```bash
# Run exactly 1 task (4 phases)
--min-cycles 4 --max-cycles 4

# Run 2-3 tasks (8-12 phases)
--min-cycles 8 --max-cycles 12

# Run 5-10 tasks (20-40 phases)
--min-cycles 20 --max-cycles 40

# Run at least 1 task, but stop after 5 tasks
--min-cycles 4 --max-cycles 20
```

## Project Structure

When creating a new project, the script:

1. Creates directory in `projects/` (or specified path)
2. Generates `README.md` with project description
3. Creates `@fix_plan.md` with initial task
4. Sets up basic structure (`src/`, `tests/`, `docs/`, `specs/`)

## Working on Root Directory

You can work directly on the ralph-ollama-standalone project itself instead of creating projects in the `projects/` folder.

### Methods

1. **Using `--root` flag:**

   ```bash
   ./scripts/ralph-loop.sh --prompt "Add feature" --root
   ```

2. **Using `--work-on-root` flag:**

   ```bash
   ./scripts/ralph-loop.sh --prompt "Add feature" --work-on-root
   ```

3. **Using special path values:**
   ```bash
   ./scripts/ralph-loop.sh --prompt "Add feature" --project-path .
   # or
   ./scripts/ralph-loop.sh --prompt "Add feature" --project-path root
   # or
   ./scripts/ralph-loop.sh --prompt "Add feature" --project-path ROOT
   ```

### Safety Confirmation

When working on the root directory, a confirmation prompt is shown:

```
⚠️  WARNING: You are about to work on the root directory.
This will modify files in: /path/to/ralph-ollama-standalone

This will work directly on the ralph-ollama-standalone project itself.
Continue? (yes/no):
```

- Type `yes` or `y` to proceed
- Type anything else to cancel
- This prevents accidental modifications to the main project

### Use Cases

- Improving the ralph-ollama-standalone project itself
- Adding features to core libraries
- Refactoring existing code
- Working on the main `@fix_plan.md` in the root directory

## How It Works

1. **Initialization**

   - Sets up project directory
   - Initializes `RalphLoopEngine`
   - Adds prompt as task/description

2. **Loop Execution**

   - Reads tasks from `@fix_plan.md`
   - For each task, executes 4 phases:
     - **Study**: Analyzes requirements
     - **Implement**: Creates code files
     - **Test**: Validates implementation
     - **Update**: Marks task complete

3. **Cycle Monitoring**

   - Counts completed phases
   - Stops when `max-cycles` reached (hard limit)
   - Stops when no tasks remain AND `min-cycles` met (soft limit)

4. **Progress Output**
   - Shows current cycle count
   - Displays current phase and task
   - Reports progress percentages (if verbose)

## Tips

1. **Start Small**: Use `--min-cycles 4 --max-cycles 8` for testing
2. **Be Specific**: Clear prompts produce better results
3. **Use Existing Projects**: Continue work on existing projects with `--project-path`
4. **Monitor Progress**: Use `--verbose` to see detailed status
5. **Model Selection**: Use `codellama` for code-heavy tasks, `llama3.2` for general tasks

## Troubleshooting

### Script Not Found

```bash
# Make sure you're in the project root
cd /path/to/ralph-ollama-standalone
./scripts/ralph-loop.sh --help
```

### Ollama Not Available

```bash
# Check if Ollama server is running
ollama serve

# Or check connection
curl http://localhost:11434/api/tags
```

### Virtual Environment Issues

The script auto-activates `venv/` if present. If issues occur:

```bash
source venv/bin/activate
python3 scripts/ralph-loop.py --help
```

## See Also

- `scripts/ralph-ollama.sh` - General Ollama integration script
- `scripts/improve-code.py` - Continuous code improvement
- `lib/ralph_loop_engine.py` - Core loop engine implementation
