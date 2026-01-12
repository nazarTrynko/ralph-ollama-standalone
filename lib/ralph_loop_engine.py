#!/usr/bin/env python3
"""
Ralph Loop Engine
Core engine for executing Ralph workflow loops programmatically with phase support.
"""

import os
import sys
import re
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from integration.ralph_ollama_adapter import RalphOllamaAdapter, call_llm
from lib.file_tracker import FileTracker
from lib.response_cache import get_cache
from lib.logging_config import get_logger
from lib.code_validator import CodeValidator

logger = get_logger('ralph_loop')


class Phase(Enum):
    """Ralph workflow phases."""
    STUDY = "study"
    IMPLEMENT = "implement"
    TEST = "test"
    UPDATE = "update"
    IDLE = "idle"
    COMPLETE = "complete"
    ERROR = "error"


class LoopMode(Enum):
    """Execution mode."""
    NON_STOP = "non_stop"
    PHASE_BY_PHASE = "phase_by_phase"


class RalphLoopEngine:
    """Engine for executing Ralph workflow loops."""
    
    def __init__(
        self,
        project_path: Path,
        adapter: Optional[RalphOllamaAdapter] = None,
        model: Optional[str] = None
    ):
        """Initialize Ralph loop engine.
        
        Args:
            project_path: Path to the project directory
            adapter: Optional Ralph adapter (creates new one if not provided)
            model: Optional model name to use for all LLM calls (overrides task-based selection)
        """
        self.project_path = Path(project_path).resolve()
        self.adapter = adapter or RalphOllamaAdapter()
        self.model = model  # Store model preference for all LLM calls
        self.file_tracker = FileTracker(self.project_path)
        self.code_validator = CodeValidator(self.project_path)
        
        self.mode = LoopMode.PHASE_BY_PHASE
        self.current_phase = Phase.IDLE
        self.current_task: Optional[str] = None
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        
        self.status_log: List[Dict[str, Any]] = []
        self.phase_history: List[Dict[str, Any]] = []
        self.user_input: Optional[str] = None
        
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        
        self.status_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Error recovery settings
        self.max_retries = 2
        self.retry_delay = 2  # seconds
        self.continue_on_non_critical = True
        
        # Progress tracking
        self.phase_start_time: Optional[datetime] = None
        self.task_start_time: Optional[datetime] = None
        self.current_phase_progress: float = 0.0  # 0.0 to 1.0
        self.files_expected: int = 0
        self.files_created_count: int = 0
        self.phase_durations: Dict[str, List[float]] = {}  # Track historical phase durations
        
        # Project metadata
        self.project_name: Optional[str] = None
        self.project_description: Optional[str] = None
    
    def set_status_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback for status updates.
        
        Args:
            callback: Function to call with status updates
        """
        self.status_callback = callback
    
    def _emit_status(self, status: Dict[str, Any]) -> None:
        """Emit status update via callback.
        
        Args:
            status: Status dictionary
        """
        if self.status_callback:
            try:
                self.status_callback(status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    def _calculate_phase_progress(self, phase: Phase) -> float:
        """Calculate progress within current phase.
        
        Args:
            phase: Current phase
            
        Returns:
            Progress value between 0.0 and 1.0
        """
        if phase == Phase.STUDY:
            # Study phase: simple time-based estimate
            if self.phase_start_time:
                elapsed = (datetime.now() - self.phase_start_time).total_seconds()
                avg_duration = self._get_average_phase_duration(phase.value)
                if avg_duration > 0:
                    return min(0.9, elapsed / avg_duration)  # Cap at 90% until complete
            return 0.3
        elif phase == Phase.IMPLEMENT:
            # Implement phase: based on files created
            if self.files_expected > 0:
                return min(0.95, self.files_created_count / max(1, self.files_expected))
            # Time-based fallback
            if self.phase_start_time:
                elapsed = (datetime.now() - self.phase_start_time).total_seconds()
                avg_duration = self._get_average_phase_duration(phase.value)
                if avg_duration > 0:
                    return min(0.9, elapsed / avg_duration)
            return 0.4
        elif phase == Phase.TEST:
            # Test phase: time-based
            if self.phase_start_time:
                elapsed = (datetime.now() - self.phase_start_time).total_seconds()
                avg_duration = self._get_average_phase_duration(phase.value)
                if avg_duration > 0:
                    return min(0.9, elapsed / avg_duration)
            return 0.5
        elif phase == Phase.UPDATE:
            # Update phase: quick, usually 80% done immediately
            return 0.8
        return 0.0
    
    def _get_average_phase_duration(self, phase_name: str) -> float:
        """Get average duration for a phase based on history.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Average duration in seconds, or 0 if no history
        """
        if phase_name not in self.phase_durations or not self.phase_durations[phase_name]:
            # Default estimates (in seconds)
            defaults = {
                'study': 30.0,
                'implement': 60.0,
                'test': 20.0,
                'update': 5.0
            }
            return defaults.get(phase_name, 30.0)
        
        durations = self.phase_durations[phase_name]
        return sum(durations) / len(durations)
    
    def _estimate_time_remaining(self, phase: Phase) -> Optional[float]:
        """Estimate time remaining for current phase.
        
        Args:
            phase: Current phase
            
        Returns:
            Estimated seconds remaining, or None if cannot estimate
        """
        if not self.phase_start_time:
            return None
        
        elapsed = (datetime.now() - self.phase_start_time).total_seconds()
        avg_duration = self._get_average_phase_duration(phase.value)
        
        if avg_duration <= 0:
            return None
        
        remaining = max(0, avg_duration - elapsed)
        return remaining
    
    def _calculate_task_progress(self) -> float:
        """Calculate overall task progress.
        
        Returns:
            Progress value between 0.0 and 1.0
        """
        phases = [Phase.STUDY, Phase.IMPLEMENT, Phase.TEST, Phase.UPDATE]
        total_phases = len(phases)
        
        # Count completed phases
        completed = 0
        for phase in phases:
            # Check if phase is in history and completed
            for entry in self.phase_history:
                if entry.get('phase') == phase.value and entry.get('success'):
                    completed += 1
                    break
        
        # Add current phase progress
        if self.current_phase in phases:
            phase_index = phases.index(self.current_phase)
            if phase_index >= completed:
                # Current phase is in progress
                phase_progress = self._calculate_phase_progress(self.current_phase)
                return (completed + phase_progress) / total_phases
        
        return completed / total_phases
    
    def _log_status(self, message: str, phase: Optional[Phase] = None, **kwargs: Any) -> None:
        """Log status message with progress information.
        
        Args:
            message: Status message
            phase: Current phase (optional)
            **kwargs: Additional status data
        """
        current_phase = phase or self.current_phase
        phase_progress = self._calculate_phase_progress(current_phase)
        task_progress = self._calculate_task_progress()
        time_remaining = self._estimate_time_remaining(current_phase)
        
        status_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'phase': current_phase.value,
            'phase_progress': round(phase_progress, 2),
            'task_progress': round(task_progress, 2),
            'time_remaining': round(time_remaining, 1) if time_remaining else None,
            'files_created': self.files_created_count,
            'files_expected': self.files_expected if self.files_expected > 0 else None,
            **kwargs
        }
        self.status_log.append(status_entry)
        logger.info(f"[{status_entry['phase']}] {message} (Progress: {int(task_progress * 100)}%)")
        self._emit_status(status_entry)
    
    def initialize_project(
        self,
        project_name: str,
        description: str,
        initial_task: Optional[str] = None
    ) -> None:
        """Initialize a new project.
        
        Args:
            project_name: Name of the project
            description: Project description/idea
            initial_task: Initial task to add to @fix_plan.md
        """
        self._log_status(f"Initializing project: {project_name}", Phase.IDLE)
        
        # Store project metadata
        self.project_name = project_name
        self.project_description = description
        
        # Create project directory
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # Create basic structure
        (self.project_path / 'src').mkdir(exist_ok=True)
        (self.project_path / 'tests').mkdir(exist_ok=True)
        (self.project_path / 'docs').mkdir(exist_ok=True)
        (self.project_path / 'specs').mkdir(exist_ok=True)
        
        # Create README
        readme_content = f"""# {project_name}

{description}

## Project Status

This project was initialized by Ralph Loop Engine.

## Getting Started

See @fix_plan.md for current tasks.
"""
        (self.project_path / 'README.md').write_text(readme_content)
        
        # Initialize @fix_plan.md
        if initial_task:
            fix_plan_content = f"""# Fix Plan - Prioritized Task List

> This file tracks prioritized tasks for the Ralph autonomous development workflow.
> Tasks are marked with `[ ]` for incomplete and `[x]` for complete.

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}

---

## High Priority

> Critical functionality, blocking work, or core features

- [ ] {initial_task}

---

## Medium Priority

> Important but not blocking, enhancements, nice-to-have features

---

## Low Priority

> Polish, optimizations, future enhancements

---

## Completed Tasks

> Moved here for reference after completion

---
"""
        else:
            fix_plan_content = f"""# Fix Plan - Prioritized Task List

> This file tracks prioritized tasks for the Ralph autonomous development workflow.
> Tasks are marked with `[ ]` for incomplete and `[x]` for complete.

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}

---

## High Priority

> Critical functionality, blocking work, or core features

---

## Medium Priority

> Important but not blocking, enhancements, nice-to-have features

---

## Low Priority

> Polish, optimizations, future enhancements

---

## Completed Tasks

> Moved here for reference after completion

---
"""
        
        (self.project_path / '@fix_plan.md').write_text(fix_plan_content)
        
        # Start file tracking
        self.file_tracker.start_tracking()
        
        self._log_status(f"Project initialized: {project_name}", Phase.IDLE)
    
    def _read_fix_plan(self) -> List[str]:
        """Read tasks from @fix_plan.md.
        
        Returns:
            List of uncompleted task descriptions
        """
        fix_plan_path = self.project_path / '@fix_plan.md'
        if not fix_plan_path.exists():
            return []
        
        tasks = []
        in_priority_section = False
        
        with open(fix_plan_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Check if we're in a priority section
                if line.startswith('## High Priority') or line.startswith('## Medium Priority') or line.startswith('## Low Priority'):
                    in_priority_section = True
                    continue
                if line.startswith('##'):
                    in_priority_section = False
                    continue
                
                # Look for uncompleted tasks
                if in_priority_section and line.startswith('- [ ]'):
                    task = line[5:].strip()
                    if task:
                        tasks.append(task)
        
        return tasks
    
    def _generate_tasks_from_description(self) -> List[str]:
        """Generate initial tasks from project description using LLM.
        
        Returns:
            List of generated task descriptions
        """
        if not self.project_description:
            # Try to read from README if description not stored
            readme_path = self.project_path / 'README.md'
            if readme_path.exists():
                content = readme_path.read_text()
                # Extract description (first paragraph after title)
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('# '):
                        # Found title, description should be in next non-empty lines
                        desc_lines = []
                        for j in range(i + 1, len(lines)):
                            if lines[j].strip() and not lines[j].startswith('#'):
                                desc_lines.append(lines[j].strip())
                            elif lines[j].startswith('#'):
                                break
                        if desc_lines:
                            self.project_description = ' '.join(desc_lines)
                        break
        
        if not self.project_description:
            return []
        
        self._log_status("Generating tasks from project description", Phase.IDLE)
        
        system_prompt = """You are Ralph, an autonomous AI development agent.
Your role is to break down project ideas into actionable tasks.

Given a project description, generate 3-5 specific, actionable tasks that need to be completed.
Tasks should be:
- Specific and clear
- Actionable (can be implemented)
- Ordered logically (most important first)
- Focused on creating deliverables or core functionality

Return ONLY a list of tasks, one per line, without numbering or bullet points.
Each task should be a single line describing what needs to be done."""
        
        prompt = f"""Project Name: {self.project_name or 'Unknown'}

Project Description:
{self.project_description}

Generate 3-5 specific, actionable tasks to get started with this project.
List one task per line, without numbering or bullets."""
        
        try:
            # Check if adapter is available before attempting to generate
            if not self.adapter.check_available():
                self._log_status("Ollama adapter not available, cannot generate tasks automatically", Phase.ERROR)
                return []
            
            result = self.adapter.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,  # Use stored model preference
                task_type="implementation"
            )
            
            response = result.get('content', '')
            
            # Parse response into task list
            tasks = []
            for line in response.strip().split('\n'):
                line = line.strip()
                # Remove common prefixes like "- ", "* ", numbers, etc.
                line = re.sub(r'^[-*•]\s*', '', line)
                line = re.sub(r'^\d+[.)]\s*', '', line)
                if line and len(line) > 10:  # Filter out very short lines
                    tasks.append(line)
            
            if tasks:
                self._log_status(f"Generated {len(tasks)} tasks from description", Phase.IDLE)
            else:
                self._log_status("Could not parse generated tasks", Phase.IDLE)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error generating tasks: {e}")
            self._log_status(f"Error generating tasks: {e}", Phase.ERROR)
            return []
    
    def _add_tasks_to_fix_plan(self, tasks: List[str]) -> bool:
        """Add tasks to @fix_plan.md in High Priority section.
        
        Args:
            tasks: List of task descriptions to add
            
        Returns:
            True if tasks were added successfully
        """
        if not tasks:
            return False
        
        fix_plan_path = self.project_path / '@fix_plan.md'
        
        # Read existing content or create template
        if fix_plan_path.exists():
            content = fix_plan_path.read_text()
        else:
            content = f"""# Fix Plan - Prioritized Task List

> This file tracks prioritized tasks for the Ralph autonomous development workflow.
> Tasks are marked with `[ ]` for incomplete and `[x]` for complete.

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}

---

## High Priority

> Critical functionality, blocking work, or core features

---

## Medium Priority

> Important but not blocking, enhancements, nice-to-have features

---

## Low Priority

> Polish, optimizations, future enhancements

---

## Completed Tasks

> Moved here for reference after completion

---

"""
        
        # Find High Priority section and insert tasks
        lines = content.split('\n')
        new_lines = []
        high_priority_found = False
        tasks_added = False
        after_description = False
        
        for i, line in enumerate(lines):
            # Check if we're at the High Priority section header
            if line.strip() == '## High Priority':
                high_priority_found = True
                new_lines.append(line)
                continue
            
            # After High Priority header, look for the description line (starts with >)
            if high_priority_found and not after_description:
                new_lines.append(line)
                if line.strip().startswith('>'):
                    after_description = True
                continue
            
            # After description, insert tasks before the next section separator or header
            if high_priority_found and after_description and not tasks_added:
                # Check if this is the end of High Priority section
                if line.strip().startswith('---') or (line.strip().startswith('##') and line.strip() != '## High Priority'):
                    # Insert tasks before this separator/header
                    for task in tasks:
                        new_lines.append(f"- [ ] {task}")
                    new_lines.append('')  # Add blank line before separator
                    tasks_added = True
                
                new_lines.append(line)
                continue
            
            # Default: just add the line
            new_lines.append(line)
        
        # If High Priority section wasn't found, append it at the end
        if not high_priority_found:
            new_lines.append('\n## High Priority\n\n> Critical functionality, blocking work, or core features\n')
            for task in tasks:
                new_lines.append(f"- [ ] {task}")
            new_lines.append('\n---\n')
            tasks_added = True
        
        content = '\n'.join(new_lines)
        fix_plan_path.write_text(content)
        
        return tasks_added
    
    def _phase_study(self, task: str) -> Dict[str, Any]:
        """Execute Study phase.
        
        Args:
            task: Task description
            
        Returns:
            Phase result dictionary
        """
        self._log_status(f"Studying task: {task}", Phase.STUDY)
        
        system_prompt = """You are Ralph, an autonomous AI development agent. 
Your role is to study and understand tasks before implementing them.

Analyze the task and provide:
1. What needs to be done
2. Key requirements
3. Dependencies or prerequisites
4. Implementation approach

Be concise and focused."""
        
        # Include user context if available
        context_note = ""
        if self.user_input and self.user_input != task:
            context_note = f"\n\nAdditional context from user:\n{self.user_input}\n"
        
        prompt = f"""Study and analyze this task:

{task}{context_note}

Provide a clear analysis of what needs to be done, key requirements, and an implementation approach."""
        
        try:
            response = call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,  # Use stored model preference
                task_type="code-review"
            )
            
            self._log_status(f"Study complete: {len(response)} chars", Phase.STUDY)
            
            return {
                'success': True,
                'output': response,
                'phase': Phase.STUDY.value
            }
        except Exception as e:
            logger.error(f"Error in Study phase: {e}")
            return {
                'success': False,
                'error': str(e),
                'phase': Phase.STUDY.value
            }
    
    def _phase_implement(self, task: str, study_output: Optional[str] = None) -> Dict[str, Any]:
        """Execute Implement phase.
        
        Args:
            task: Task description
            study_output: Output from Study phase (optional)
            
        Returns:
            Phase result dictionary
        """
        self._log_status(f"Implementing task: {task}", Phase.IMPLEMENT)
        
        system_prompt = """You are Ralph, an autonomous AI development agent.
Your role is to implement code and create files based on tasks.

When implementing:
1. Create necessary files and directories
2. Write clean, well-structured code
3. Follow best practices
4. Include appropriate comments
5. Handle errors appropriately

Provide code blocks with file paths clearly marked."""
        
        context = f"Task: {task}\n"
        if study_output:
            context += f"\nStudy Analysis:\n{study_output}\n"
        
        # Include user context if available
        if self.user_input and self.user_input != task:
            context += f"\nAdditional context from user:\n{self.user_input}\n"
        
        prompt = f"""{context}

Implement this task. Provide the code with clear file paths. Format your response as:

```path/to/file.py
# code here
```

For multiple files, provide each file separately."""
        
        try:
            response = call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,  # Use stored model preference
                task_type="implementation"
            )
            
            # Parse response to extract file paths and code
            files_created = self._parse_code_blocks(response)
            
            # Set expected files count for progress tracking
            self.files_expected = len(files_created)
            self.files_created_count = 0
            
            if not files_created:
                self._log_status("No code blocks found in response", Phase.IMPLEMENT)
                return {
                    'success': False,
                    'error': 'No code blocks found in LLM response',
                    'phase': Phase.IMPLEMENT.value
                }
            
            # Validate files before writing
            validation_results = self.code_validator.validate_and_execute(
                files_created,
                execute=False,  # Don't execute during implement phase
                run_tests=False
            )
            
            # Report validation errors and warnings
            if validation_results['errors']:
                for error in validation_results['errors']:
                    self._log_status(f"Validation error: {error}", Phase.IMPLEMENT)
                    logger.warning(f"Code validation error: {error}")
            
            if validation_results['warnings']:
                for warning in validation_results['warnings']:
                    self._log_status(f"Validation warning: {warning}", Phase.IMPLEMENT)
                    logger.info(f"Code validation warning: {warning}")
            
            # Write files to disk (even if validation found issues, but log them)
            written_files = []
            execution_results = []
            
            for i, file_info in enumerate(files_created):
                file_path = self.project_path / file_info['path']
                
                # Get validation result for this file
                validation = None
                if i < len(validation_results['validated']):
                    validation = validation_results['validated'][i]
                
                try:
                    # Create parent directories if needed
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Only write if validation passed (or if warnings only, or no validation available)
                    should_write = True
                    if validation:
                        should_write = validation['valid'] or (not validation['errors'] and validation['warnings'])
                    
                    if should_write:
                        # Write file content
                        file_path.write_text(file_info['content'])
                        written_files.append(str(file_path.relative_to(self.project_path)))
                        self.files_created_count += 1
                        self._log_status(
                            f"Created file: {file_info['path']} ({self.files_created_count}/{self.files_expected})",
                            Phase.IMPLEMENT
                        )
                        
                        # If it's a Python file and validation passed, try to execute it
                        if file_path.suffix == '.py':
                            if not validation or validation['valid']:
                                exec_result = self.code_validator.execute_python_file(file_path)
                                execution_results.append({
                                    'file': file_info['path'],
                                    'success': exec_result['success'],
                                    'error': exec_result.get('error'),
                                    'stdout': exec_result.get('stdout', '')[:500],  # Limit output
                                    'stderr': exec_result.get('stderr', '')[:500]
                                })
                                
                                if exec_result['success']:
                                    self._log_status(f"Executed {file_info['path']} successfully", Phase.IMPLEMENT)
                                else:
                                    self._log_status(f"Execution warning for {file_info['path']}: {exec_result.get('error', 'Unknown error')}", Phase.IMPLEMENT)
                    else:
                        # Skip writing invalid files
                        error_msg = ', '.join(validation['errors']) if validation and validation['errors'] else 'Validation failed'
                        self._log_status(f"Skipped invalid file: {file_info['path']} - {error_msg}", Phase.IMPLEMENT)
                        logger.warning(f"Skipping invalid file {file_info['path']}: {error_msg}")
                        
                except Exception as e:
                    logger.error(f"Error writing file {file_info['path']}: {e}")
                    self._log_status(f"Error writing file {file_info['path']}: {e}", Phase.IMPLEMENT)
            
            # Check if any test files were created
            test_files = [f for f in written_files if 'test' in Path(f).name.lower()]
            
            # Run tests if test files were created
            test_results = None
            if test_files:
                self._log_status(f"Test files detected, running tests...", Phase.IMPLEMENT)
                test_results = self.code_validator.run_tests()
                if test_results['success']:
                    self._log_status(f"Tests passed: {test_results.get('tests_passed', 0)}", Phase.IMPLEMENT)
                else:
                    self._log_status(f"Tests failed or had issues: {test_results.get('error', 'Unknown')}", Phase.IMPLEMENT)
            
            self._log_status(
                f"Implementation complete: {len(written_files)} files written",
                Phase.IMPLEMENT,
                files_created=len(written_files),
                execution_results=execution_results,
                test_results=test_results
            )
            
            return {
                'success': True,
                'output': response,
                'files_created': written_files,
                'validation_results': validation_results,
                'execution_results': execution_results,
                'test_results': test_results,
                'phase': Phase.IMPLEMENT.value
            }
        except Exception as e:
            logger.error(f"Error in Implement phase: {e}")
            return {
                'success': False,
                'error': str(e),
                'phase': Phase.IMPLEMENT.value
            }
    
    def _parse_code_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse code blocks from LLM response.
        
        Supports multiple formats:
        - ```path/to/file.py\ncode``` (file path)
        - ```python\ncode``` (language tag)
        - ```path with spaces/file.py\ncode``` (paths with spaces)
        - ```file: path/to/file.py\ncode``` (explicit file marker)
        - ```path: path/to/file.py\ncode``` (path marker)
        - ```create: path/to/file.py\ncode``` (create marker)
        - Inline code blocks (single backticks) are ignored
        
        Args:
            response: LLM response text
            
        Returns:
            List of dictionaries with 'path' and 'content' keys
            
        Examples:
            >>> engine = RalphLoopEngine(Path("/tmp"))
            >>> response = "```src/main.py\\ndef main(): pass\\n```"
            >>> files = engine._parse_code_blocks(response)
            >>> files[0]['path']
            'src/main.py'
        """
        files = []
        # Pattern for code blocks (triple backticks only, not inline)
        # Group 1: optional specifier (path, language, or empty)
        # Group 2: code content
        # Use negative lookbehind/lookahead to avoid matching inline code
        pattern = r'```([^\n`]*)\n(.*?)```'
        
        matches = re.finditer(pattern, response, re.DOTALL)
        for match in matches:
            specifier = match.group(1).strip() if match.group(1) else None
            content = match.group(2).strip()
            
            # Skip empty or whitespace-only blocks
            if not content:
                continue
            
            # Determine if specifier is a file path or language tag
            file_path = self._extract_file_path(specifier, content, len(files))
            
            files.append({
                'path': file_path,
                'content': content
            })
        
        return files
    
    def _sanitize_file_path(self, path: str) -> str:
        """Sanitize a file path to ensure it's safe for filesystem.
        
        Args:
            path: Raw file path string
            
        Returns:
            Sanitized file path string
        """
        # Remove newlines and carriage returns
        path = path.replace('\n', '').replace('\r', '')
        
        # Remove invalid filesystem characters (OS-dependent, but common ones)
        # Windows: < > : " | ? * \
        # Unix: / (and null byte, but that's handled by filesystem)
        invalid_chars = '<>:"|?*\\'
        for char in invalid_chars:
            path = path.replace(char, '_')
        
        # Limit path length (OS limit is typically 255 bytes for filename)
        # We'll limit to 200 characters to be safe and account for directory path
        if len(path) > 200:
            # Try to preserve extension if present
            if '.' in path:
                name, ext = path.rsplit('.', 1)
                if len(ext) <= 10:  # Reasonable extension length
                    # Truncate name part, keep extension
                    max_name_len = 200 - len(ext) - 1  # -1 for the dot
                    path = name[:max_name_len] + '.' + ext
                else:
                    path = path[:200]
            else:
                path = path[:200]
        
        # Remove leading/trailing dots and spaces (invalid on Windows)
        path = path.strip('. ')
        
        # Ensure path is not empty
        if not path:
            path = 'file'
        
        return path
    
    def _extract_file_path(self, specifier: Optional[str], content: str, file_index: int) -> str:
        """Extract file path from code block specifier or content.
        
        Args:
            specifier: The specifier from code block (path, language, or None)
            content: Code block content
            file_index: Current file index for default naming
            
        Returns:
            File path string (sanitized and validated)
        """
        # Common programming language tags (not file paths)
        language_tags = {
            'python', 'javascript', 'js', 'typescript', 'ts', 'java', 'cpp', 'c++', 'c',
            'go', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'sql', 'html',
            'css', 'json', 'yaml', 'yml', 'xml', 'markdown', 'md', 'bash', 'sh', 'shell',
            'powershell', 'ps1', 'dockerfile', 'makefile', 'cmake', 'txt', 'plaintext'
        }
        
        # If specifier exists, check if it's a path or language
        if specifier:
            specifier_lower = specifier.lower().strip()
            
            # Check for explicit file markers (file:, path:, create:, save:, write:)
            marker_patterns = [
                (r'^file:\s*(.+)', 'file:'),
                (r'^path:\s*(.+)', 'path:'),
                (r'^create:\s*(.+)', 'create:'),
                (r'^save:\s*(.+)', 'save:'),
                (r'^write:\s*(.+)', 'write:'),
            ]
            
            for pattern, marker in marker_patterns:
                match = re.match(pattern, specifier, re.IGNORECASE)
                if match:
                    path = match.group(1).strip()
                    # Remove quotes if present
                    path = path.strip('"\'`')
                    if path:
                        return self._sanitize_file_path(path)
            
            # Check if it looks like a file path
            # Path indicators: contains /, \, or has file extension pattern
            has_path_separator = '/' in specifier or '\\' in specifier
            has_extension = '.' in specifier and len(specifier.split('.')[-1]) <= 5  # reasonable extension length
            
            # Handle special characters in paths (URL-encoded, escaped, etc.)
            # Decode common special characters
            decoded_specifier = specifier
            # Handle URL-encoded spaces and special chars
            try:
                import urllib.parse
                decoded_specifier = urllib.parse.unquote(specifier)
            except Exception:
                pass
            
            # If it has path indicators and is not a known language tag
            if (has_path_separator or has_extension) and specifier_lower not in language_tags:
                # Return decoded version if it's different and valid
                if decoded_specifier != specifier and (has_path_separator or has_extension):
                    return self._sanitize_file_path(decoded_specifier)
                return self._sanitize_file_path(specifier)
            
            # If it's a known language tag or a description (neither path nor language), ignore it
            if specifier_lower in language_tags:
                specifier = None  # Treat as language tag, not path
            else:
                # Specifier is neither a path nor a language tag - likely a description
                # Ignore it and fall through to content extraction or default naming
                specifier = None
        
        # Try to extract path from content
        # Look for patterns like "file: path", "path: path", "create: path"
        # Limit search to first 500 chars to avoid false matches in large code blocks
        content_preview = content[:500] if len(content) > 500 else content
        path_patterns = [
            r'(?:file|path|create|save|write)[:\s]+([^\s\n]+(?:\s+[^\s\n]+)*)',  # Handles paths with spaces
            r'#\s*(?:file|path|create)[:\s]+([^\n]+)',  # Comment-based path hints
            r'@file\s+([^\s\n]+)',  # @file annotation
            r'<!--\s*file:\s*([^\s]+)\s*-->',  # HTML comment
        ]
        
        for pattern in path_patterns:
            path_match = re.search(pattern, content_preview, re.IGNORECASE)
            if path_match:
                extracted_path = path_match.group(1).strip()
                # Clean up common prefixes/suffixes
                extracted_path = re.sub(r'^(?:file|path|create|save|write)[:\s]+', '', extracted_path, flags=re.IGNORECASE)
                extracted_path = extracted_path.strip('"\'`<>')
                # Limit extracted path length to avoid false matches
                if extracted_path and len(extracted_path) <= 200:
                    return self._sanitize_file_path(extracted_path)
        
        # Try to infer file extension from content (language detection)
        inferred_ext = self._infer_file_extension(content)
        
        # Default: generate a name based on index with inferred extension
        result = f"generated_{file_index}{inferred_ext}"
        return result
    
    def _infer_file_extension(self, content: str) -> str:
        """Infer file extension from code content.
        
        Args:
            content: Code content
            
        Returns:
            File extension (e.g., '.py', '.js', etc.)
        """
        content_lower = content.lower().strip()
        
        # Python indicators
        if any(keyword in content_lower for keyword in ['def ', 'import ', 'from ', 'class ', 'if __name__']):
            return '.py'
        
        # JavaScript/TypeScript indicators
        if any(keyword in content_lower for keyword in ['function ', 'const ', 'let ', 'var ', 'export ', 'import ']):
            if 'typescript' in content_lower or 'interface ' in content_lower or ': ' in content[:100]:
                return '.ts'
            return '.js'
        
        # HTML indicators
        if content_lower.strip().startswith('<!doctype') or '<html' in content_lower or '<div' in content_lower:
            return '.html'
        
        # CSS indicators
        if '{' in content and ':' in content and ('color:' in content_lower or 'margin:' in content_lower):
            return '.css'
        
        # JSON indicators
        if (content.strip().startswith('{') and content.strip().endswith('}')) or \
           (content.strip().startswith('[') and content.strip().endswith(']')):
            try:
                import json
                json.loads(content)
                return '.json'
            except Exception:
                pass
        
        # Markdown indicators
        if any(marker in content_lower for marker in ['# ', '## ', '```', '**', '* ']):
            return '.md'
        
        # Shell script indicators
        if content_lower.startswith('#!/bin/') or content_lower.startswith('#!/usr/bin/'):
            return '.sh'
        
        # Default to .py if no match
        return '.py'
    
    def _phase_test(self, task: str) -> Dict[str, Any]:
        """Execute Test phase.
        
        Args:
            task: Task description
            
        Returns:
            Phase result dictionary
        """
        self._log_status(f"Testing task: {task}", Phase.TEST)
        
        system_prompt = """You are Ralph, an autonomous AI development agent.
Your role is to test and validate implementations.

Analyze the implementation and provide:
1. Test cases that should be run
2. Expected outcomes
3. Potential issues or edge cases
4. Validation steps

Be concise and practical."""
        
        prompt = f"""For this task:

{task}

Provide test cases and validation steps. If tests exist, suggest running them. If not, suggest what tests should be created."""
        
        try:
            response = call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,  # Use stored model preference
                task_type="testing"
            )
            
            self._log_status(f"Test analysis complete: {len(response)} chars", Phase.TEST)
            
            return {
                'success': True,
                'output': response,
                'phase': Phase.TEST.value
            }
        except Exception as e:
            logger.error(f"Error in Test phase: {e}")
            return {
                'success': False,
                'error': str(e),
                'phase': Phase.TEST.value
            }
    
    def _phase_update(self, task: str) -> Dict[str, Any]:
        """Execute Update phase.
        
        Args:
            task: Task description
            
        Returns:
            Phase result dictionary
        """
        self._log_status(f"Updating status for task: {task}", Phase.UPDATE)
        
        # Mark task as complete in @fix_plan.md
        fix_plan_path = self.project_path / '@fix_plan.md'
        if fix_plan_path.exists():
            content = fix_plan_path.read_text()
            # Replace first occurrence of task with completed version
            pattern = rf'(- \[ \] {re.escape(task)})'
            replacement = f'- [x] {task}'
            content = re.sub(pattern, replacement, content, count=1)
            fix_plan_path.write_text(content)
        
        self._log_status(f"Status updated: task marked complete", Phase.UPDATE)
        
        return {
            'success': True,
            'output': f"Task '{task}' marked as complete",
            'phase': Phase.UPDATE.value
        }
    
    def _is_critical_error(self, error: str, phase: Phase) -> bool:
        """Determine if an error is critical (should stop execution).
        
        Args:
            error: Error message
            phase: Current phase
            
        Returns:
            True if error is critical
        """
        # Critical errors that should stop execution
        critical_patterns = [
            'permission denied',
            'disk full',
            'out of memory',
            'connection refused',
            'timeout',
            'authentication failed',
            'invalid api key'
        ]
        
        error_lower = error.lower()
        for pattern in critical_patterns:
            if pattern in error_lower:
                return True
        
        # UPDATE phase errors are usually non-critical (just marking tasks)
        if phase == Phase.UPDATE:
            return False
        
        # Other errors are generally non-critical (can retry or continue)
        return False
    
    def _execute_phase(self, phase: Phase, task: str, previous_output: Optional[str] = None, retry_count: int = 0) -> Dict[str, Any]:
        """Execute a single phase with retry logic.
        
        Args:
            phase: Phase to execute
            task: Current task
            previous_output: Output from previous phase (optional)
            retry_count: Current retry attempt (0 = first attempt)
            
        Returns:
            Phase result dictionary
        """
        with self.lock:
            self.current_phase = phase
        
        # Track phase start time for progress calculation
        phase_start = datetime.now()
        self.phase_start_time = phase_start
        
        phase_entry = {
            'phase': phase.value,
            'task': task,
            'started_at': phase_start.isoformat(),
            'completed_at': None,
            'success': False,
            'output': None,
            'error': None,
            'retry_count': retry_count
        }
        
        # Reset phase-specific progress
        self.current_phase_progress = 0.0
        self.files_created_count = 0
        self.files_expected = 0
        
        try:
            if phase == Phase.STUDY:
                result = self._phase_study(task)
            elif phase == Phase.IMPLEMENT:
                result = self._phase_implement(task, previous_output)
            elif phase == Phase.TEST:
                result = self._phase_test(task)
            elif phase == Phase.UPDATE:
                result = self._phase_update(task)
            else:
                result = {'success': False, 'error': f'Unknown phase: {phase}'}
            
            phase_end = datetime.now()
            phase_duration = (phase_end - phase_start).total_seconds()
            
            # Track phase duration for future estimates
            if phase.value not in self.phase_durations:
                self.phase_durations[phase.value] = []
            self.phase_durations[phase.value].append(phase_duration)
            # Keep only last 10 durations
            if len(self.phase_durations[phase.value]) > 10:
                self.phase_durations[phase.value] = self.phase_durations[phase.value][-10:]
            
            phase_entry['completed_at'] = phase_end.isoformat()
            phase_entry['duration'] = round(phase_duration, 2)
            phase_entry['success'] = result.get('success', False)
            phase_entry['output'] = result.get('output')
            phase_entry['error'] = result.get('error')
            
            # Update progress to 100% for completed phase
            self.current_phase_progress = 1.0
            
            # If phase failed, check if we should retry
            if not result.get('success', False) and retry_count < self.max_retries:
                error = result.get('error', 'Unknown error')
                
                # Check if error is critical
                if self._is_critical_error(error, phase):
                    self._log_status(f"Critical error in {phase.value} phase: {error}. Stopping.", phase)
                    phase_entry['error'] = f"Critical: {error}"
                    self.phase_history.append(phase_entry)
                    return result
                
                # Non-critical error - retry
                self._log_status(
                    f"Phase {phase.value} failed (attempt {retry_count + 1}/{self.max_retries + 1}): {error}. Retrying...",
                    phase
                )
                time.sleep(self.retry_delay)
                return self._execute_phase(phase, task, previous_output, retry_count + 1)
            
            # If still failed after retries, check if we should continue
            if not result.get('success', False) and self.continue_on_non_critical:
                error = result.get('error', 'Unknown error')
                if not self._is_critical_error(error, phase):
                    self._log_status(
                        f"Phase {phase.value} failed after {retry_count + 1} attempts: {error}. Continuing anyway.",
                        phase
                    )
                    # Mark as success with warning
                    result['success'] = True
                    result['warning'] = f"Phase completed with errors: {error}"
            
            self.phase_history.append(phase_entry)
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing phase {phase.value}: {e}")
            
            # Check if we should retry
            if retry_count < self.max_retries and not self._is_critical_error(error_msg, phase):
                self._log_status(
                    f"Exception in {phase.value} phase (attempt {retry_count + 1}/{self.max_retries + 1}): {error_msg}. Retrying...",
                    phase
                )
                time.sleep(self.retry_delay)
                return self._execute_phase(phase, task, previous_output, retry_count + 1)
            
            phase_entry['completed_at'] = datetime.now().isoformat()
            phase_entry['error'] = error_msg
            phase_entry['success'] = False
            
            # If non-critical and continue_on_non_critical is True, mark as success with warning
            if self.continue_on_non_critical and not self._is_critical_error(error_msg, phase):
                phase_entry['success'] = True
                phase_entry['warning'] = f"Phase completed with exception: {error_msg}"
                self._log_status(f"Phase {phase.value} had exception but continuing: {error_msg}", phase)
            
            self.phase_history.append(phase_entry)
            
            return {
                'success': phase_entry['success'],
                'error': error_msg,
                'warning': phase_entry.get('warning'),
                'phase': phase.value
            }
    
    def _wait_for_resume(self) -> None:
        """Wait for resume signal (for phase-by-phase mode)."""
        while self.is_paused and not self.should_stop:
            time.sleep(0.5)
    
    def _run_loop(self) -> None:
        """Main loop execution (runs in separate thread)."""
        try:
            self._log_status("Starting Ralph loop", Phase.IDLE)
            
            # Get initial file snapshot
            self.file_tracker.start_tracking()
            
            while not self.should_stop:
                # Get next task
                tasks = self._read_fix_plan()
                if not tasks:
                    # Try to generate tasks from project description
                    generated_tasks = self._generate_tasks_from_description()
                    if generated_tasks:
                        if self._add_tasks_to_fix_plan(generated_tasks):
                            self._log_status(f"Auto-generated {len(generated_tasks)} tasks, continuing", Phase.IDLE)
                            # Re-read tasks after adding them
                            tasks = self._read_fix_plan()
                    
                    # If still no tasks after generation attempt, complete
                    if not tasks:
                        self._log_status("No more tasks, loop complete", Phase.COMPLETE)
                        with self.lock:
                            self.current_phase = Phase.COMPLETE
                            self.is_running = False
                        break
                
                self.current_task = tasks[0]
                self.task_start_time = datetime.now()
                self._log_status(f"Starting task: {self.current_task}", Phase.IDLE)
                
                # Execute phases
                phases = [Phase.STUDY, Phase.IMPLEMENT, Phase.TEST, Phase.UPDATE]
                previous_output = None
                
                for phase in phases:
                    if self.should_stop:
                        break
                    
                    # Check if paused (phase-by-phase mode)
                    if self.mode == LoopMode.PHASE_BY_PHASE and phase != Phase.STUDY:
                        self._wait_for_resume()
                        if self.should_stop:
                            break
                    
                    # Execute phase
                    result = self._execute_phase(phase, self.current_task, previous_output)
                    
                    if not result.get('success'):
                        error_msg = result.get('error', 'Unknown error')
                        warning = result.get('warning')
                        
                        if warning:
                            self._log_status(f"Phase {phase.value} completed with warning: {warning}", phase)
                        else:
                            self._log_status(f"Phase {phase.value} failed: {error_msg}", Phase.ERROR)
                            
                            # Check if error is critical
                            if self._is_critical_error(error_msg, phase):
                                self._log_status("Critical error detected. Stopping loop.", Phase.ERROR)
                                with self.lock:
                                    self.current_phase = Phase.ERROR
                                    self.is_running = False
                                break
                        
                        # Continue to next phase if non-critical or continue_on_non_critical is True
                        if not self.continue_on_non_critical and not warning:
                            self._log_status("Non-critical error but continue_on_non_critical is False. Stopping.", Phase.ERROR)
                            break
                    
                    previous_output = result.get('output')
                    
                    # Update file tracking
                    changes = self.file_tracker.update_snapshot()
                    if changes['created'] or changes['modified']:
                        self._log_status(
                            f"Files changed: {len(changes['created'])} created, {len(changes['modified'])} modified",
                            phase
                        )
                        # Invalidate file list cache (will be invalidated by session_id in UI)
                        # Cache invalidation happens at UI level when files change
                    
                    # Pause after phase if in phase-by-phase mode
                    if self.mode == LoopMode.PHASE_BY_PHASE:
                        with self.lock:
                            self.is_paused = True
                        self._log_status(f"Paused after {phase.value} phase", phase)
                        self._wait_for_resume()
                
                # Move to next task
                if not self.should_stop:
                    self.current_task = None
                    time.sleep(1)  # Brief pause between tasks
                    
        except Exception as e:
            logger.error(f"Error in loop execution: {e}")
            self._log_status(f"Loop error: {str(e)}", Phase.ERROR)
            with self.lock:
                self.current_phase = Phase.ERROR
                self.is_running = False
    
    def start(self, mode: LoopMode = LoopMode.PHASE_BY_PHASE) -> None:
        """Start the loop execution.
        
        Args:
            mode: Execution mode
        """
        if self.is_running:
            raise RuntimeError("Loop is already running")
        
        with self.lock:
            self.mode = mode
            self.is_running = True
            self.is_paused = False
            self.should_stop = False
            self.current_phase = Phase.IDLE
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        self._log_status(f"Loop started in {mode.value} mode", Phase.IDLE)
    
    def pause(self) -> None:
        """Pause execution."""
        with self.lock:
            self.is_paused = True
        self._log_status("Loop paused", self.current_phase)
    
    def resume(self, user_input: Optional[str] = None) -> None:
        """Resume execution.
        
        Args:
            user_input: Optional user input/feedback
        """
        self.user_input = user_input
        with self.lock:
            self.is_paused = False
        self._log_status("Loop resumed", self.current_phase, user_input=user_input is not None)
    
    def stop(self) -> None:
        """Stop execution."""
        with self.lock:
            self.should_stop = True
            self.is_paused = False
        self._log_status("Loop stopped", Phase.IDLE)
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        with self.lock:
            self.is_running = False
            self.current_phase = Phase.IDLE
    
    def set_mode(self, mode: LoopMode) -> None:
        """Change execution mode.
        
        Args:
            mode: New execution mode
        """
        with self.lock:
            old_mode = self.mode
            self.mode = mode
            
            # If switching from phase-by-phase to non-stop, resume if paused
            if old_mode == LoopMode.PHASE_BY_PHASE and mode == LoopMode.NON_STOP:
                self.is_paused = False
        
        self._log_status(f"Mode changed: {old_mode.value} → {mode.value}", self.current_phase)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status with progress information.
        
        Returns:
            Status dictionary
        """
        with self.lock:
            phase_progress = self._calculate_phase_progress(self.current_phase)
            task_progress = self._calculate_task_progress()
            time_remaining = self._estimate_time_remaining(self.current_phase)
            
            # Calculate task elapsed time
            task_elapsed = None
            if self.task_start_time:
                task_elapsed = (datetime.now() - self.task_start_time).total_seconds()
            
            # Calculate phase elapsed time
            phase_elapsed = None
            if self.phase_start_time:
                phase_elapsed = (datetime.now() - self.phase_start_time).total_seconds()
            
            return {
                'is_running': self.is_running,
                'is_paused': self.is_paused,
                'mode': self.mode.value,
                'current_phase': self.current_phase.value,
                'current_task': self.current_task,
                'phase_history': self.phase_history[-10:],  # Last 10 phases
                'status_log': self.status_log[-20:],  # Last 20 log entries
                'files': self.file_tracker.get_all_files(),
                'progress': {
                    'phase_progress': round(phase_progress, 2),
                    'task_progress': round(task_progress, 2),
                    'time_remaining': round(time_remaining, 1) if time_remaining else None,
                    'phase_elapsed': round(phase_elapsed, 1) if phase_elapsed else None,
                    'task_elapsed': round(task_elapsed, 1) if task_elapsed else None,
                    'files_created': self.files_created_count,
                    'files_expected': self.files_expected if self.files_expected > 0 else None,
                }
            }
