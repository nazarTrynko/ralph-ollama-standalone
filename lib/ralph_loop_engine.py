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
from lib.logging_config import get_logger

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
        adapter: Optional[RalphOllamaAdapter] = None
    ):
        """Initialize Ralph loop engine.
        
        Args:
            project_path: Path to the project directory
            adapter: Optional Ralph adapter (creates new one if not provided)
        """
        self.project_path = Path(project_path).resolve()
        self.adapter = adapter or RalphOllamaAdapter()
        self.file_tracker = FileTracker(self.project_path)
        
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
    
    def _log_status(self, message: str, phase: Optional[Phase] = None, **kwargs: Any) -> None:
        """Log status message.
        
        Args:
            message: Status message
            phase: Current phase (optional)
            **kwargs: Additional status data
        """
        status_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'phase': (phase or self.current_phase).value,
            **kwargs
        }
        self.status_log.append(status_entry)
        logger.info(f"[{status_entry['phase']}] {message}")
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
        
        prompt = f"""Study and analyze this task:

{task}

Provide a clear analysis of what needs to be done, key requirements, and an implementation approach."""
        
        try:
            response = call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
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
                task_type="implementation"
            )
            
            # Parse response to extract file paths and code
            files_created = self._parse_code_blocks(response)
            
            # Write files to disk
            written_files = []
            for file_info in files_created:
                file_path = self.project_path / file_info['path']
                try:
                    # Create parent directories if needed
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    # Write file content
                    file_path.write_text(file_info['content'])
                    written_files.append(str(file_path.relative_to(self.project_path)))
                    self._log_status(f"Created file: {file_info['path']}", Phase.IMPLEMENT)
                except Exception as e:
                    logger.error(f"Error writing file {file_info['path']}: {e}")
                    self._log_status(f"Error writing file {file_info['path']}: {e}", Phase.IMPLEMENT)
            
            self._log_status(
                f"Implementation complete: {len(written_files)} files written",
                Phase.IMPLEMENT,
                files_created=len(written_files)
            )
            
            return {
                'success': True,
                'output': response,
                'files_created': written_files,
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
        # Improved pattern: handles paths with spaces, language tags, and empty specifiers
        # Group 1: optional specifier (path, language, or empty)
        # Group 2: code content
        pattern = r'```([^\n]*)\n(.*?)```'
        
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
    
    def _extract_file_path(self, specifier: Optional[str], content: str, file_index: int) -> str:
        """Extract file path from code block specifier or content.
        
        Args:
            specifier: The specifier from code block (path, language, or None)
            content: Code block content
            file_index: Current file index for default naming
            
        Returns:
            File path string
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
            
            # Check for explicit file markers
            if specifier_lower.startswith('file:'):
                # Extract path after "file:"
                path = specifier[5:].strip()
                if path:
                    return path
            
            # Check if it looks like a file path
            # Path indicators: contains /, \, or has file extension pattern
            has_path_separator = '/' in specifier or '\\' in specifier
            has_extension = '.' in specifier and len(specifier.split('.')[-1]) <= 5  # reasonable extension length
            
            # If it has path indicators and is not a known language tag
            if (has_path_separator or has_extension) and specifier_lower not in language_tags:
                return specifier
            
            # If it's a known language tag, don't use it as path
            if specifier_lower in language_tags:
                specifier = None  # Treat as language tag, not path
        
        # Try to extract path from content
        # Look for patterns like "file: path", "path: path", "create: path"
        path_patterns = [
            r'(?:file|path|create|save|write)[:\s]+([^\s\n]+(?:\s+[^\s\n]+)*)',  # Handles paths with spaces
            r'#\s*(?:file|path)[:\s]+([^\n]+)',  # Comment-based path hints
        ]
        
        for pattern in path_patterns:
            path_match = re.search(pattern, content, re.IGNORECASE)
            if path_match:
                extracted_path = path_match.group(1).strip()
                # Clean up common prefixes/suffixes
                extracted_path = re.sub(r'^(?:file|path|create|save|write)[:\s]+', '', extracted_path, flags=re.IGNORECASE)
                extracted_path = extracted_path.strip('"\'`')
                if extracted_path:
                    return extracted_path
        
        # Default: generate a name based on index
        return f"generated_{file_index}.py"
    
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
    
    def _execute_phase(self, phase: Phase, task: str, previous_output: Optional[str] = None) -> Dict[str, Any]:
        """Execute a single phase.
        
        Args:
            phase: Phase to execute
            task: Current task
            previous_output: Output from previous phase (optional)
            
        Returns:
            Phase result dictionary
        """
        with self.lock:
            self.current_phase = phase
        
        phase_entry = {
            'phase': phase.value,
            'task': task,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'success': False,
            'output': None,
            'error': None
        }
        
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
            
            phase_entry['completed_at'] = datetime.now().isoformat()
            phase_entry['success'] = result.get('success', False)
            phase_entry['output'] = result.get('output')
            phase_entry['error'] = result.get('error')
            
            self.phase_history.append(phase_entry)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing phase {phase.value}: {e}")
            phase_entry['completed_at'] = datetime.now().isoformat()
            phase_entry['error'] = str(e)
            self.phase_history.append(phase_entry)
            
            return {
                'success': False,
                'error': str(e),
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
                    self._log_status("No more tasks, loop complete", Phase.COMPLETE)
                    with self.lock:
                        self.current_phase = Phase.COMPLETE
                        self.is_running = False
                    break
                
                self.current_task = tasks[0]
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
                        self._log_status(f"Phase {phase.value} failed: {result.get('error')}", Phase.ERROR)
                        # Continue to next phase anyway
                    
                    previous_output = result.get('output')
                    
                    # Update file tracking
                    changes = self.file_tracker.update_snapshot()
                    if changes['created'] or changes['modified']:
                        self._log_status(
                            f"Files changed: {len(changes['created'])} created, {len(changes['modified'])} modified",
                            phase
                        )
                    
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
        """Get current status.
        
        Returns:
            Status dictionary
        """
        with self.lock:
            return {
                'is_running': self.is_running,
                'is_paused': self.is_paused,
                'mode': self.mode.value,
                'current_phase': self.current_phase.value,
                'current_task': self.current_task,
                'phase_history': self.phase_history[-10:],  # Last 10 phases
                'status_log': self.status_log[-20:],  # Last 20 log entries
                'files': self.file_tracker.get_all_files()
            }
