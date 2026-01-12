#!/usr/bin/env python3
"""
Task Parser for Ralph Loop Engine
Handles reading, parsing, and managing tasks from @fix_plan.md files.
"""

import re
from pathlib import Path
from typing import List, Optional, Callable, Any
from datetime import datetime
from lib.logging_config import get_logger

logger = get_logger('task_parser')


class TaskParser:
    """Parser for reading and managing tasks from @fix_plan.md files."""
    
    def __init__(
        self,
        project_path: Path,
        project_name: Optional[str] = None,
        project_description: Optional[str] = None,
        adapter: Optional[Any] = None,
        model: Optional[str] = None,
        log_callback: Optional[Callable[[str, Any], None]] = None
    ):
        """Initialize task parser.
        
        Args:
            project_path: Path to project directory
            project_name: Optional project name
            project_description: Optional project description
            adapter: Optional LLM adapter for task generation
            model: Optional model name for LLM calls
            log_callback: Optional callback for logging (message, phase)
        """
        self.project_path = Path(project_path).resolve()
        self.project_name = project_name
        self.project_description = project_description
        self.adapter = adapter
        self.model = model
        self.log_callback = log_callback
    
    def read_tasks(self) -> List[str]:
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
    
    def generate_tasks_from_description(self) -> List[str]:
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
        
        if self.log_callback:
            self.log_callback("Generating tasks from project description", None)
        
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
            if not self.adapter or not self.adapter.check_available():
                if self.log_callback:
                    self.log_callback("Ollama adapter not available, cannot generate tasks automatically", None)
                return []
            
            result = self.adapter.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,
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
                if self.log_callback:
                    self.log_callback(f"Generated {len(tasks)} tasks from description", None)
            else:
                if self.log_callback:
                    self.log_callback("Could not parse generated tasks", None)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error generating tasks: {e}")
            if self.log_callback:
                self.log_callback(f"Error generating tasks: {e}", None)
            return []
    
    def add_tasks_to_fix_plan(self, tasks: List[str]) -> bool:
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
    
    def mark_task_complete(self, task: str) -> bool:
        """Mark a task as complete in @fix_plan.md.
        
        Args:
            task: Task description to mark as complete
            
        Returns:
            True if task was marked complete
        """
        fix_plan_path = self.project_path / '@fix_plan.md'
        if not fix_plan_path.exists():
            return False
        
        content = fix_plan_path.read_text()
        # Replace first occurrence of task with completed version
        pattern = rf'(- \[ \] {re.escape(task)})'
        replacement = f'- [x] {task}'
        new_content = re.sub(pattern, replacement, content, count=1)
        
        if new_content != content:
            fix_plan_path.write_text(new_content)
            return True
        
        return False
