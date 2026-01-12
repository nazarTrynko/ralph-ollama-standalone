# Ralph Loop Script - Quick Start

## TL;DR

Run Ralph autonomous development loops with cycle control:

```bash
./scripts/ralph-loop.sh --prompt "Your task description" --min-cycles 4 --max-cycles 12
```

## Common Examples

### Create New Project (1-3 tasks)

```bash
./scripts/ralph-loop.sh \
  --prompt "Create a Python CLI todo manager" \
  --min-cycles 4 \
  --max-cycles 12
```

### Continue Existing Project

```bash
./scripts/ralph-loop.sh \
  --prompt "Add error handling" \
  --project-path projects/Video_ideas \
  --min-cycles 8 \
  --max-cycles 20
```

### Use Code-Focused Model

```bash
./scripts/ralph-loop.sh \
  --prompt "Implement JWT authentication" \
  --model codellama \
  --min-cycles 4 \
  --max-cycles 16
```

### Work on Root Directory

```bash
./scripts/ralph-loop.sh \
  --prompt "Add new feature to core engine" \
  --root \
  --min-cycles 4 \
  --max-cycles 8
```

_Note: Shows confirmation prompt before proceeding_

## Key Concepts

- **One Cycle** = One phase (Study, Implement, Test, or Update)
- **One Task** = 4 cycles (one of each phase)
- **min-cycles**: Minimum phases before stopping (soft limit)
- **max-cycles**: Maximum phases allowed (hard limit)

## Cycle Examples

| Cycles | Tasks      | Command                           |
| ------ | ---------- | --------------------------------- |
| 4      | 1 task     | `--min-cycles 4 --max-cycles 4`   |
| 8-12   | 2-3 tasks  | `--min-cycles 8 --max-cycles 12`  |
| 20-40  | 5-10 tasks | `--min-cycles 20 --max-cycles 40` |

## Full Documentation

See `scripts/RALPH_LOOP_USAGE.md` for complete documentation.
