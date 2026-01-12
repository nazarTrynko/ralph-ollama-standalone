# Rules Index: Quick Reference

**Purpose:** Fast navigation and quick reference for Ralph workflow rules

---

## Rule Priority Table

| Priority | Rule File | Purpose | Always Apply |
|----------|-----------|---------|--------------|
| **1** | `ralph-core.mdc` | Core workflow and objectives | ✅ Yes |
| **2** | `ralph-status.mdc` | Status reporting format (CRITICAL) | ✅ Yes |
| **3** | `ralph-rate-limits.mdc` | Rate limit detection and handling | ✅ Yes |
| **4** | `ralph-completion.mdc` | Completion detection logic | ✅ Yes |
| **5** | `ralph-priorities.mdc` | Task prioritization rules | ✅ Yes |

---

## Quick Links

### Core Rules

- **[ralph-core.mdc](ralph-core.mdc)** - Main workflow: Study specs → Review priorities → Implement ONE task → Test → Update
- **[ralph-status.mdc](ralph-status.mdc)** - Status block format (MANDATORY at end of every response)
- **[ralph-priorities.mdc](ralph-priorities.mdc)** - Task selection from `@fix_plan.md`

### Safety & Control

- **[ralph-rate-limits.mdc](ralph-rate-limits.mdc)** - Prevents infinite loops (detects rate limits)
- **[ralph-completion.mdc](ralph-completion.mdc)** - Knows when to stop (completion criteria)

---

## Status Block Quick Reference

**Format (MANDATORY):**
```
---RALPH_STATUS---
STATUS: IN_PROGRESS | COMPLETE | BLOCKED
TASKS_COMPLETED_THIS_LOOP: <number>
FILES_MODIFIED: <number>
TESTS_STATUS: PASSING | FAILING | NOT_RUN
WORK_TYPE: IMPLEMENTATION | TESTING | DOCUMENTATION | REFACTORING
EXIT_SIGNAL: false | true
RECOMMENDATION: <one line summary>
---END_RALPH_STATUS---
```

**When to Set EXIT_SIGNAL: true:**
- All tasks in `@fix_plan.md` marked [x] AND tests passing
- Rate limit detected
- Same error repeated 3+ times with no progress
- No meaningful work remains

---

## Common Workflows

### Starting a Ralph Loop

1. Open new conversation in Cursor
2. Say: "Follow the Ralph workflow. Work on the highest priority task from @fix_plan.md"
3. Rules automatically guide AI through workflow
4. Check `RALPH_STATUS` block at end

### Loop Control

- **Continue:** `EXIT_SIGNAL: false` → Start next conversation
- **Stop:** `EXIT_SIGNAL: true` → Work complete or rate limited

---

## Integration Points

### Project Files

- **`@fix_plan.md`** - Task priorities (read for priorities, updated when tasks complete)
- **`specs/prd-auraflix.md`** - Project requirements
- **`specs/prd.json`** - User story requirements
- **`PROMPT.md`** - Detailed workflow instructions (reference)

### Rule Dependencies

- `ralph-core.mdc` → references `ralph-status.mdc` (status blocks)
- `ralph-core.mdc` → references `@fix_plan.md` (priorities)
- `ralph-completion.mdc` → references `@fix_plan.md` (completion check)
- `ralph-priorities.mdc` → references `@fix_plan.md` (task selection)
- `ralph-rate-limits.mdc` → sets `EXIT_SIGNAL: true` (overrides all)

---

## Rule Categories

### Workflow Rules
- `ralph-core.mdc` - Primary workflow engine
- `ralph-priorities.mdc` - Task selection logic

### Control Rules
- `ralph-status.mdc` - Status reporting (enables loop control)
- `ralph-completion.mdc` - Completion detection
- `ralph-rate-limits.mdc` - Safety mechanism

---

## Quick Decision Tree

```
Need to understand rules?
│
├─► Quick overview → [README.md](README.md)
├─► Visual diagrams → [ARCHITECTURE.md](ARCHITECTURE.md)
├─► This file → Quick reference
│
Need specific rule?
│
├─► Workflow → [ralph-core.mdc](ralph-core.mdc)
├─► Status format → [ralph-status.mdc](ralph-status.mdc)
├─► Task selection → [ralph-priorities.mdc](ralph-priorities.mdc)
├─► Completion → [ralph-completion.mdc](ralph-completion.mdc)
└─► Rate limits → [ralph-rate-limits.mdc](ralph-rate-limits.mdc)
```

---

**See Also:**
- [README.md](README.md) - Comprehensive guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Visual documentation and rule relationships
