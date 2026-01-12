#!/usr/bin/env python3
"""
Ralph Loop Script
Command-line interface for running Ralph loops with cycle control and prompt input.
"""

import sys
import os
import time
import argparse
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from lib.path_utils import setup_paths
setup_paths()

from lib.ralph_loop_engine import RalphLoopEngine, LoopMode, Phase
from integration.ralph_ollama_adapter import RalphOllamaAdapter
from lib.logging_config import get_logger

logger = get_logger('ralph_loop_script')


class RalphLoopRunner:
    """Runner for Ralph loops with cycle control."""
    
    def __init__(
        self,
        project_path: Path,
        prompt: str,
        min_cycles: int = 4,
        max_cycles: int = 40,
        model: Optional[str] = None,
        mode: LoopMode = LoopMode.NON_STOP,
        verbose: bool = False
    ):
        """Initialize Ralph loop runner.
        
        Args:
            project_path: Path to project directory
            prompt: User prompt/command (used as description, task, and context)
            min_cycles: Minimum number of phases to execute
            max_cycles: Maximum number of phases to execute
            model: Ollama model to use (optional)
            mode: Loop execution mode
            verbose: Enable verbose output
        """
        self.project_path = Path(project_path).resolve()
        self.prompt = prompt
        self.min_cycles = min_cycles
        self.max_cycles = max_cycles
        self.model = model
        self.mode = mode
        self.verbose = verbose
        
        # Initialize adapter
        self.adapter = RalphOllamaAdapter()
        if not self.adapter.check_available():
            raise RuntimeError("Ollama adapter not available. Check server connection.")
        
        # Initialize engine with model preference
        self.engine = RalphLoopEngine(self.project_path, self.adapter, model=self.model)
        
        # Cycle tracking
        self.phase_count = 0
        self.last_phase_count = 0
        
        # Project metadata
        self.project_name: Optional[str] = None
        self.is_new_project = False
    
    def _sanitize_project_name(self, name: str) -> str:
        """Sanitize project name for filesystem.
        
        Args:
            name: Project name
            
        Returns:
            Sanitized name
        """
        # Remove special characters, keep alphanumeric, spaces, hyphens, underscores
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        # Limit length
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        return safe_name or "ralph_project"
    
    def _generate_project_name(self) -> str:
        """Generate project name from prompt.
        
        Returns:
            Project name
        """
        # Use first 50 chars of prompt, sanitized
        name = self.prompt[:50].strip()
        return self._sanitize_project_name(name)
    
    def _setup_project(self) -> None:
        """Set up project directory and initialize if needed."""
        # Check if project exists
        if self.project_path.exists():
            readme_path = self.project_path / 'README.md'
            if readme_path.exists():
                # Try to extract project name from README
                content = readme_path.read_text()
                match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if match:
                    self.project_name = match.group(1).strip()
                else:
                    self.project_name = self.project_path.name
                self.is_new_project = False
                if self.verbose:
                    print(f"📁 Using existing project: {self.project_name}")
            else:
                # Directory exists but no README - treat as new
                self.is_new_project = True
                self.project_name = self._generate_project_name()
        else:
            # New project
            self.is_new_project = True
            self.project_name = self._generate_project_name()
            self.project_path.mkdir(parents=True, exist_ok=True)
            if self.verbose:
                print(f"📁 Creating new project: {self.project_name}")
        
        # Initialize project if new or if no @fix_plan.md exists
        fix_plan_path = self.project_path / '@fix_plan.md'
        if self.is_new_project or not fix_plan_path.exists():
            # Use prompt as description
            initial_task = self.prompt if self.is_new_project else None
            self.engine.initialize_project(
                project_name=self.project_name,
                description=self.prompt,
                initial_task=initial_task
            )
            if self.verbose:
                print(f"✅ Project initialized: {self.project_name}")
        else:
            # Existing project - check if we should add prompt as task
            tasks = self.engine._read_fix_plan()
            if not tasks:
                # No tasks, add prompt as initial task
                self.engine._add_tasks_to_fix_plan([self.prompt])
                if self.verbose:
                    print(f"📝 Added prompt as initial task")
        
        # Store prompt as user context
        self.engine.user_input = self.prompt
    
    def _count_phases(self) -> int:
        """Count completed phases from phase history.
        
        Returns:
            Number of completed phases
        """
        status = self.engine.get_status()
        phase_history = status.get('phase_history', [])
        
        # Count phases that completed successfully or with warnings
        count = 0
        for entry in phase_history:
            if entry.get('success') or entry.get('warning'):
                # Only count actual workflow phases (not IDLE, ERROR, COMPLETE)
                phase = entry.get('phase', '')
                if phase in ['study', 'implement', 'test', 'update']:
                    count += 1
        
        return count
    
    def _should_continue(self) -> bool:
        """Check if loop should continue based on cycle limits.
        
        Returns:
            True if should continue, False if should stop
        """
        self.phase_count = self._count_phases()
        
        # Hard limit: stop if max_cycles reached
        if self.phase_count >= self.max_cycles:
            return False
        
        # Check if engine is still running
        status = self.engine.get_status()
        if not status.get('is_running', False):
            # Engine stopped - check if we met min_cycles
            if self.phase_count >= self.min_cycles:
                return False
            # If min not met but no more tasks, stop anyway
            tasks = self.engine._read_fix_plan()
            if not tasks:
                return False
        
        return True
    
    def _print_status(self) -> None:
        """Print current status."""
        status = self.engine.get_status()
        current_phase = status.get('current_phase', 'idle')
        current_task = status.get('current_task', 'None')
        progress = status.get('progress', {})
        
        # Calculate cycles
        self.phase_count = self._count_phases()
        
        # Print status
        if self.phase_count != self.last_phase_count:
            print(f"\n🔄 Cycle {self.phase_count}/{self.max_cycles} (min: {self.min_cycles})")
            self.last_phase_count = self.phase_count
        
        if self.verbose:
            phase_progress = progress.get('phase_progress', 0.0)
            task_progress = progress.get('task_progress', 0.0)
            print(f"   Phase: {current_phase} ({int(phase_progress * 100)}%)")
            print(f"   Task: {current_task[:60]}...")
            print(f"   Overall: {int(task_progress * 100)}%")
    
    def run(self) -> Dict[str, Any]:
        """Run the Ralph loop with cycle control.
        
        Returns:
            Dictionary with execution results
        """
        print(f"\n🚀 Starting Ralph Loop")
        print(f"   Project: {self.project_name}")
        print(f"   Prompt: {self.prompt[:60]}...")
        print(f"   Cycles: {self.min_cycles} - {self.max_cycles}")
        print(f"   Mode: {self.mode.value}")
        if self.model:
            print(f"   Model: {self.model}")
        print()
        
        # Set up project
        try:
            self._setup_project()
        except Exception as e:
            logger.error(f"Error setting up project: {e}")
            return {
                'success': False,
                'error': f"Failed to setup project: {e}",
                'phases_completed': 0
            }
        
        # Start loop
        try:
            self.engine.start(mode=self.mode)
        except Exception as e:
            logger.error(f"Error starting loop: {e}")
            return {
                'success': False,
                'error': f"Failed to start loop: {e}",
                'phases_completed': 0
            }
        
        # Monitor loop
        start_time = datetime.now()
        last_status_time = datetime.now()
        
        try:
            while self._should_continue():
                # Print status periodically
                if (datetime.now() - last_status_time).total_seconds() >= 2.0:
                    self._print_status()
                    last_status_time = datetime.now()
                
                # Check status
                status = self.engine.get_status()
                
                # If paused in phase-by-phase mode, resume automatically
                if status.get('is_paused') and self.mode == LoopMode.PHASE_BY_PHASE:
                    # In non-stop mode, we shouldn't pause, but if we do, resume
                    self.engine.resume()
                
                # Sleep briefly to avoid busy waiting
                time.sleep(0.5)
            
            # Stop loop
            self.engine.stop()
            
            # Wait for thread to finish
            if self.engine.thread and self.engine.thread.is_alive():
                self.engine.thread.join(timeout=5)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            self.engine.stop()
            if self.engine.thread and self.engine.thread.is_alive():
                self.engine.thread.join(timeout=5)
        
        # Get final status
        final_status = self.engine.get_status()
        final_phase_count = self._count_phases()
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        # Print summary
        print(f"\n✅ Loop completed")
        print(f"   Phases executed: {final_phase_count}")
        print(f"   Time elapsed: {elapsed_time:.1f}s")
        print(f"   Final phase: {final_status.get('current_phase', 'unknown')}")
        
        # Get additional stats for milestone
        files = final_status.get('files', [])
        files_count = len(files) if files else 0
        phase_history = final_status.get('phase_history', [])
        
        # Count completed tasks (UPDATE phases that succeeded)
        completed_tasks = sum(1 for entry in phase_history 
                            if entry.get('phase') == 'update' and entry.get('success'))
        
        # Print finish milestone
        print(f"\n🎯 Final Milestone")
        print(f"   Project: {self.project_name or 'Unknown'}")
        print(f"   Location: {self.project_path}")
        print(f"   Files created: {files_count}")
        print(f"   Tasks completed: {completed_tasks}")
        
        # Determine completion status
        if final_phase_count >= self.min_cycles:
            if final_phase_count >= self.max_cycles:
                print(f"   Status: Maximum cycles reached ({self.max_cycles})")
            else:
                print(f"   Status: Minimum cycles completed ({self.min_cycles})")
        else:
            print(f"   Status: Stopped early (completed {final_phase_count}/{self.min_cycles} min cycles)")
        
        # Next steps
        if files_count > 0:
            print(f"\n📁 Next steps:")
            print(f"   - Review files in: {self.project_path}")
            if self.project_path.name != '.':
                print(f"   - Check @fix_plan.md for remaining tasks")
            print(f"   - Continue development or run another loop")
        
        return {
            'success': True,
            'phases_completed': final_phase_count,
            'min_cycles': self.min_cycles,
            'max_cycles': self.max_cycles,
            'elapsed_time': elapsed_time,
            'final_status': final_status,
            'files_created': files_count,
            'tasks_completed': completed_tasks
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run Ralph loop with cycle control and prompt input',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with prompt and cycle limits
  %(prog)s --prompt "Create a simple calculator app" --min-cycles 4 --max-cycles 12

  # Use existing project
  %(prog)s --prompt "Add error handling" --project-path projects/Video_ideas --min-cycles 8 --max-cycles 20

  # Work on root directory (with confirmation)
  %(prog)s --prompt "Add new feature" --root --min-cycles 4 --max-cycles 8

  # Work on root using special path
  %(prog)s --prompt "Refactor code" --project-path . --min-cycles 4 --max-cycles 8

  # Non-stop mode with custom model
  %(prog)s --prompt "Implement user authentication" --mode non_stop --model codellama --min-cycles 4 --max-cycles 16
        """
    )
    
    parser.add_argument(
        '--prompt', '-p',
        type=str,
        required=True,
        help='Prompt/command to use as task/description/context'
    )
    
    parser.add_argument(
        '--min-cycles', '--min',
        type=int,
        default=4,
        help='Minimum number of phases to execute (default: 4 = one full task)'
    )
    
    parser.add_argument(
        '--max-cycles', '--max',
        type=int,
        default=40,
        help='Maximum number of phases to execute (default: 40 = 10 tasks)'
    )
    
    parser.add_argument(
        '--project-path',
        type=str,
        default=None,
        help='Path to project directory (default: create new in projects/). Special values: ".", "root", "ROOT" to work on root directory'
    )
    
    parser.add_argument(
        '--project-name',
        type=str,
        default=None,
        help='Project name (default: auto-generated from prompt)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Ollama model to use (optional, uses config default)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['phase_by_phase', 'non_stop'],
        default='non_stop',
        help='Loop mode (default: non_stop)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--root', '--work-on-root',
        dest='work_on_root',
        action='store_true',
        help='Work on the root directory (ralph-ollama-standalone project itself) instead of projects/ folder'
    )
    
    args = parser.parse_args()
    
    # Validate cycle limits
    if args.min_cycles < 0:
        print("❌ Error: min-cycles must be >= 0", file=sys.stderr)
        sys.exit(1)
    
    if args.max_cycles < args.min_cycles:
        print(f"❌ Error: max-cycles ({args.max_cycles}) must be >= min-cycles ({args.min_cycles})", file=sys.stderr)
        sys.exit(1)
    
    # Check if working on root directory
    is_root_directory = False
    
    # Check for --root flag (overrides project-path)
    if args.work_on_root:
        is_root_directory = True
        project_path = project_root
    # Check for special path values
    elif args.project_path:
        special_paths = ['.', 'root', 'ROOT']
        if args.project_path in special_paths:
            is_root_directory = True
            project_path = project_root
        else:
            project_path = Path(args.project_path)
    else:
        # Create in projects directory
        projects_dir = project_root / 'projects'
        projects_dir.mkdir(exist_ok=True)
        
        if args.project_name:
            project_name = args.project_name
        else:
            # Generate from prompt
            safe_name = "".join(c for c in args.prompt[:50] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            project_name = safe_name or "ralph_project"
        
        project_path = projects_dir / project_name
    
    # Show confirmation prompt if working on root directory
    if is_root_directory:
        print(f"\n⚠️  WARNING: You are about to work on the root directory.")
        print(f"This will modify files in: {project_path}")
        print(f"\nThis will work directly on the ralph-ollama-standalone project itself.")
        response = input("Continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Cancelled by user.")
            sys.exit(0)
        print("✅ Proceeding with root directory...\n")
    
    # Convert mode string to enum
    mode = LoopMode.NON_STOP if args.mode == 'non_stop' else LoopMode.PHASE_BY_PHASE
    
    # Create runner
    try:
        runner = RalphLoopRunner(
            project_path=project_path,
            prompt=args.prompt,
            min_cycles=args.min_cycles,
            max_cycles=args.max_cycles,
            model=args.model,
            mode=mode,
            verbose=args.verbose
        )
        
        # Run loop
        result = runner.run()
        
        # Exit with appropriate code
        if result.get('success'):
            sys.exit(0)
        else:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
