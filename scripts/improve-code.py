#!/usr/bin/env python3
"""
Continuous Code Improvement Script
Uses Ollama to analyze and improve code in the repository.
"""

import sys
import os
import time
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse

# Cross-platform file locking
HAS_FCNTL = False
HAS_MSVCRT = False
fcntl = None
msvcrt = None

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    pass

if not HAS_FCNTL:
    try:
        import msvcrt
        HAS_MSVCRT = True
    except ImportError:
        pass

from lib.path_utils import setup_paths
setup_paths()

from lib.ollama_client import OllamaClient
from lib.exceptions import OllamaModelError
from integration.ralph_ollama_adapter import RalphOllamaAdapter

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
IMPROVEMENT_LOG = PROJECT_ROOT / 'state' / 'improvements.json'
LOCK_FILE = PROJECT_ROOT / 'state' / '.improve-code.lock'
EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', '@venv', '.venv', 'node_modules', '.cursor', 'state'}
EXCLUDE_FILES = {'.pyc', '.pyo', '.pyd', '.so', '.dylib'}
PYTHON_EXTENSIONS = {'.py'}


class CodeImprover:
    """Continuously improves code using Ollama."""
    
    def __init__(self, model: Optional[str] = None, interval: int = 300):
        """Initialize the code improver.
        
        Args:
            model: Model to use (None = auto-select)
            interval: Seconds between improvement cycles
        """
        self.client = OllamaClient()
        self.adapter = RalphOllamaAdapter()
        self.model = self._resolve_model(model)
        self.interval = interval
        self.improvements_log = self._load_improvements_log()
        self.stats = {
            'files_analyzed': 0,
            'files_improved': 0,
            'improvements_applied': 0,
            'start_time': datetime.now().isoformat()
        }
        self.lock_file = None
        self.current_file_index = 0
        self.total_files = 0
    
    def _resolve_model(self, requested_model: Optional[str]) -> Optional[str]:
        """Resolve model name, checking availability and using fallback if needed.
        
        Args:
            requested_model: Model name requested by user (or None for auto-select)
        
        Returns:
            Available model name, or None for auto-select
        """
        # If no model specified, let adapter auto-select
        if requested_model is None:
            return None
        
        # Check if server is available
        if not self.client.check_server():
            print("⚠️  Warning: Cannot check model availability (server not running)")
            return requested_model
        
        # Get available models
        try:
            available_models = self.client.list_models()
        except Exception as e:
            print(f"⚠️  Warning: Could not list models: {e}")
            return requested_model
        
        # Normalize model names (remove tags like :latest, :4b)
        normalized_available = []
        for model in available_models:
            # Add both full name and base name
            normalized_available.append(model)
            base_name = model.split(':')[0]
            if base_name != model:
                normalized_available.append(base_name)
        
        # Check if requested model is available (exact match or base name match)
        if requested_model in normalized_available:
            return requested_model
        
        # Check if base name matches
        requested_base = requested_model.split(':')[0]
        for model in available_models:
            if model.startswith(requested_base + ':') or model == requested_base:
                print(f"ℹ️  Using '{model}' instead of '{requested_model}'")
                return model
        
        # Model not found - try to find a suitable fallback
        fallback_models = ['llama3.2', 'llama3', 'llama3.1', 'gemma3']
        for fallback in fallback_models:
            for model in available_models:
                if model.startswith(fallback + ':') or model == fallback:
                    print(f"⚠️  Model '{requested_model}' not found. Using fallback: '{model}'")
                    print(f"   Available models: {', '.join(available_models)}")
                    print(f"   To install '{requested_model}': ollama pull {requested_model}")
                    return model
        
        # Last resort: use first available model
        if available_models:
            print(f"⚠️  Model '{requested_model}' not found. Using: '{available_models[0]}'")
            print(f"   Available models: {', '.join(available_models)}")
            print(f"   To install '{requested_model}': ollama pull {requested_model}")
            return available_models[0]
        
        # No models available
        print(f"❌ Error: Model '{requested_model}' not found and no fallback available")
        print(f"   Available models: {', '.join(available_models) if available_models else 'none'}")
        print(f"   To install '{requested_model}': ollama pull {requested_model}")
        return requested_model  # Return original, let it fail with proper error
        
    def _acquire_lock(self, force: bool = False) -> bool:
        """Acquire a file lock to prevent concurrent runs.
        
        Args:
            force: If True, remove existing lock file even if process appears to be running
            
        Returns:
            True if lock acquired, False otherwise
        """
        try:
            LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if lock file exists and if process is still running
            if LOCK_FILE.exists():
                lock_age = time.time() - LOCK_FILE.stat().st_mtime
                max_lock_age = 3600 * 24  # 24 hours - consider lock stale after this
                
                try:
                    with open(LOCK_FILE, 'r') as f:
                        content = f.read().strip()
                        parts = content.split('\n', 1)
                        pid_str = parts[0]
                        timestamp_str = parts[1] if len(parts) > 1 else None
                        
                        if pid_str:
                            pid = int(pid_str)
                            
                            # Check if this is our own PID (stale lock from previous run)
                            current_pid = os.getpid()
                            if pid == current_pid:
                                print(f"⚠️  Removing stale lock file from previous run (same PID: {pid})")
                                LOCK_FILE.unlink()
                            # Check if lock is stale (older than max_lock_age)
                            elif lock_age > max_lock_age:
                                print(f"⚠️  Removing stale lock file (age: {lock_age/3600:.1f} hours)")
                                LOCK_FILE.unlink()
                            elif force:
                                print(f"⚠️  Force removing lock file (PID: {pid})")
                                LOCK_FILE.unlink()
                            else:
                                # Check if process is still running
                                process_running = False
                                try:
                                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                                    process_running = True
                                except ProcessLookupError:
                                    # Process doesn't exist
                                    process_running = False
                                except PermissionError:
                                    # Can't check process (permission denied)
                                    # Check if lock is old enough to be considered stale
                                    if lock_age > 300:  # 5 minutes
                                        print(f"⚠️  Cannot verify process (permission denied), but lock is {lock_age/60:.1f} minutes old")
                                        print(f"   Removing potentially stale lock file")
                                        LOCK_FILE.unlink()
                                    else:
                                        # Lock is recent, assume process is running
                                        process_running = True
                                except OSError:
                                    # Other error, assume process doesn't exist
                                    process_running = False
                                
                                if process_running:
                                    age_str = f"{lock_age/60:.1f} minutes" if lock_age < 3600 else f"{lock_age/3600:.1f} hours"
                                    print(f"❌ Another instance is already running (PID: {pid}, lock age: {age_str})")
                                    print(f"   Lock file: {LOCK_FILE}")
                                    print(f"   If you're sure no other instance is running:")
                                    print(f"     - Delete the lock file: rm {LOCK_FILE}")
                                    print(f"     - Or use --force flag to remove it automatically")
                                    return False
                                else:
                                    # Process doesn't exist, remove stale lock
                                    print(f"⚠️  Removing stale lock file (process {pid} not found)")
                                    LOCK_FILE.unlink()
                except (ValueError, IOError) as e:
                    # Invalid lock file, remove it
                    print(f"⚠️  Removing invalid lock file: {e}")
                    LOCK_FILE.unlink()
            
            # Create lock file
            self.lock_file = open(LOCK_FILE, 'w')
            
            # Try to acquire lock based on platform
            if HAS_FCNTL:
                # Unix/Linux/macOS
                try:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    # Another process has the lock
                    self.lock_file.close()
                    self.lock_file = None
                    print(f"❌ Could not acquire lock: another process has the file locked")
                    print(f"   Lock file: {LOCK_FILE}")
                    print(f"   Use --force to remove the lock file")
                    return False
            elif HAS_MSVCRT:
                # Windows
                try:
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                except IOError:
                    # Another process has the lock
                    self.lock_file.close()
                    self.lock_file = None
                    print(f"❌ Could not acquire lock: another process has the file locked")
                    print(f"   Lock file: {LOCK_FILE}")
                    print(f"   Use --force to remove the lock file")
                    return False
            # If neither available, we'll use file existence as lock (less safe but works)
            
            # Write PID and timestamp to lock file
            timestamp = datetime.now().isoformat()
            self.lock_file.write(f"{os.getpid()}\n{timestamp}\n")
            self.lock_file.flush()
            return True
        except (IOError, OSError) as e:
            if self.lock_file:
                try:
                    self.lock_file.close()
                except Exception:
                    pass
                self.lock_file = None
            print(f"❌ Could not acquire lock: {e}")
            print(f"   Lock file: {LOCK_FILE}")
            print(f"   If you're sure no other instance is running, delete the lock file or use --force")
            return False
    
    def _release_lock(self):
        """Release the file lock."""
        if self.lock_file:
            try:
                if HAS_FCNTL:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                elif HAS_MSVCRT:
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                self.lock_file.close()
            except Exception:
                pass
            self.lock_file = None
        
        # Remove lock file
        try:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
        except Exception:
            pass
    
    def _fix_json_escapes(self, json_str: str) -> str:
        """Fix invalid escape sequences in JSON string."""
        # Replace invalid escape sequences with valid ones
        # Common issues: \x without hex, \ followed by non-escape char
        # Strategy: Replace problematic patterns before parsing
        
        # Fix invalid \x sequences (must be followed by 2 hex digits)
        json_str = re.sub(r'\\x([^0-9a-fA-F]|$)', r'\\\\x\\1', json_str)
        json_str = re.sub(r'\\x([0-9a-fA-F])([^0-9a-fA-F]|$)', r'\\\\x\\1\\2', json_str)
        
        # Fix unescaped backslashes that aren't valid escapes
        # But be careful not to break valid escapes
        # This is tricky - we'll use a more conservative approach
        # Only fix obvious issues like \ followed by space or newline
        json_str = re.sub(r'\\([^"\\/bfnrtux])', r'\\\\\\1', json_str)
        
        return json_str
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from Ollama response, handling invalid escapes."""
        # Try to extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start < 0 or json_end <= json_start:
            return None
        
        json_str = response[json_start:json_end]
        
        # Try normal parsing first
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # If it's an escape error, try to fix it
            if 'Invalid \\escape' in str(e) or 'escape' in str(e).lower():
                try:
                    fixed_json = self._fix_json_escapes(json_str)
                    return json.loads(fixed_json)
                except json.JSONDecodeError:
                    # If fixing didn't work, try using raw_decode with error recovery
                    try:
                        # Try to find and extract just the JSON object
                        # Remove any trailing text after the closing brace
                        brace_count = 0
                        end_pos = json_start
                        for i, char in enumerate(response[json_start:], json_start):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_pos = i + 1
                                    break
                        
                        if end_pos > json_start:
                            json_str = response[json_start:end_pos]
                            fixed_json = self._fix_json_escapes(json_str)
                            return json.loads(fixed_json)
                    except Exception:
                        pass
            
            # Last resort: try to extract a valid JSON subset
            # This is a fallback that might lose some data
            return None
    
    def _load_improvements_log(self) -> Dict:
        """Load improvement history."""
        if IMPROVEMENT_LOG.exists():
            try:
                with open(IMPROVEMENT_LOG) as f:
                    return json.load(f)
            except Exception:
                return {'improvements': [], 'last_run': None}
        return {'improvements': [], 'last_run': None}
    
    def _save_improvements_log(self):
        """Save improvement history."""
        IMPROVEMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        self.improvements_log['last_run'] = datetime.now().isoformat()
        with open(IMPROVEMENT_LOG, 'w') as f:
            json.dump(self.improvements_log, f, indent=2)
    
    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the project."""
        files = []
        for root, dirs, filenames in os.walk(PROJECT_ROOT):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            # Also check if current root is in an excluded directory
            root_path = Path(root)
            if any(excluded_dir in root_path.parts for excluded_dir in EXCLUDE_DIRS):
                continue
            
            for filename in filenames:
                filepath = Path(root) / filename
                
                # Double-check: skip if any part of the path is in excluded dirs
                if any(excluded_dir in filepath.parts for excluded_dir in EXCLUDE_DIRS):
                    continue
                
                if filepath.suffix in PYTHON_EXTENSIONS:
                    if filepath.suffix not in EXCLUDE_FILES:
                        files.append(filepath)
        return files
    
    def _has_recent_improvements(self, filepath: Path) -> bool:
        """Check if file was recently improved."""
        rel_path = str(filepath.relative_to(PROJECT_ROOT))
        for improvement in self.improvements_log.get('improvements', []):
            if improvement.get('file') == rel_path:
                # Skip if improved in last hour
                improved_time = datetime.fromisoformat(improvement.get('timestamp', '2000-01-01'))
                time_diff = (datetime.now() - improved_time).total_seconds()
                if time_diff < 3600:  # 1 hour
                    return True
        return False
    
    def _analyze_code(self, filepath: Path) -> Optional[Dict]:
        """Analyze a file and suggest improvements."""
        try:
            with open(filepath) as f:
                content = f.read()
        except Exception as e:
            print(f"  ⚠️  Could not read {filepath}: {e}")
            return None
        
        # Skip if file is too large (> 50KB)
        if len(content) > 50000:
            print(f"  ⏭️  Skipping {filepath.name} (too large)")
            return None
        
        # Skip if recently improved
        if self._has_recent_improvements(filepath):
            print(f"  ⏭️  Skipping {filepath.name} (recently improved)")
            return None
        
        rel_path = str(filepath.relative_to(PROJECT_ROOT))
        
        prompt = f"""Analyze this Python code and suggest specific improvements:

File: {rel_path}

```python
{content}
```

Provide improvements in this exact JSON format:
{{
  "needs_improvement": true/false,
  "improvements": [
    {{
      "type": "bug_fix|refactor|optimization|style|documentation",
      "description": "What to improve",
      "code": "Improved code snippet",
      "line_start": number,
      "line_end": number,
      "reason": "Why this improvement"
    }}
  ],
  "overall_score": 0-100,
  "summary": "Brief summary of improvements"
}}

Only suggest improvements if they are:
1. Safe (won't break functionality)
2. Clear and specific
3. Actually improve the code
4. Follow Python best practices

If code is already excellent, set needs_improvement to false."""

        try:
            result = self.adapter.generate(
                prompt=prompt,
                task_type="code-review",
                model=self.model,
                system_prompt="You are an expert Python code reviewer. Provide specific, actionable improvements in JSON format only."
            )
            
            response = result.get('content', '')
            
            # Parse JSON with error handling
            analysis = self._parse_json_response(response)
            if analysis:
                return analysis
            else:
                print(f"  ⚠️  Could not parse JSON from response for {filepath.name}")
                # Debug: show a snippet of the response
                if len(response) > 200:
                    print(f"  Response preview: {response[:200]}...")
                return None
                
        except OllamaModelError as e:
            # Model error - try to use fallback
            print(f"  ⚠️  Model error: {e}")
            if hasattr(e, 'available_models') and e.available_models:
                print(f"  Available models: {', '.join(e.available_models)}")
            # Try with None to let adapter auto-select
            try:
                print(f"  🔄 Retrying with auto-selected model...")
                result = self.adapter.generate(
                    prompt=prompt,
                    task_type="code-review",
                    model=None,  # Let adapter auto-select
                    system_prompt="You are an expert Python code reviewer. Provide specific, actionable improvements in JSON format only."
                )
                response = result.get('content', '')
                analysis = self._parse_json_response(response)
                if analysis:
                    return analysis
            except Exception as retry_error:
                print(f"  ❌ Retry also failed: {retry_error}")
            return None
        except Exception as e:
            print(f"  ⚠️  Error analyzing {filepath.name}: {e}")
            return None
    
    def _apply_improvement(self, filepath: Path, improvement: Dict) -> bool:
        """Apply a single improvement to a file."""
        try:
            with open(filepath) as f:
                lines = f.readlines()
            
            line_start = improvement.get('line_start', 1) - 1
            line_end = improvement.get('line_end', len(lines))
            
            if line_start < 0 or line_end > len(lines):
                print(f"    ⚠️  Invalid line numbers: {line_start+1}-{line_end}")
                return False
            
            # Get improved code
            improved_code = improvement.get('code', '')
            if not improved_code:
                return False
            
            # Replace the lines
            new_lines = lines[:line_start] + [improved_code + '\n'] + lines[line_end:]
            
            # Write back
            with open(filepath, 'w') as f:
                f.writelines(new_lines)
            
            return True
            
        except Exception as e:
            print(f"    ⚠️  Error applying improvement: {e}")
            return False
    
    def _apply_improvements(self, filepath: Path, improvements: List[Dict]) -> int:
        """Apply multiple improvements to a file."""
        applied = 0
        # Apply in reverse order to maintain line numbers
        for improvement in reversed(improvements):
            if self._apply_improvement(filepath, improvement):
                applied += 1
                print(f"    ✅ Applied: {improvement.get('type', 'unknown')} - {improvement.get('description', '')[:50]}")
        return applied
    
    def improve_file(self, filepath: Path) -> bool:
        """Improve a single file."""
        rel_path = str(filepath.relative_to(PROJECT_ROOT))
        self.current_file_index += 1
        progress = f"[{self.current_file_index}/{self.total_files}]" if self.total_files > 0 else ""
        print(f"\n📄 {progress} Analyzing: {rel_path}")
        start_time = time.time()
        
        analysis = self._analyze_code(filepath)
        elapsed = time.time() - start_time
        if elapsed > 1:
            print(f"  ⏱️  Analysis took {elapsed:.1f}s")
        if not analysis:
            return False
        
        if not analysis.get('needs_improvement', False):
            print(f"  ✅ Code is already good (score: {analysis.get('overall_score', 'N/A')})")
            return False
        
        improvements = analysis.get('improvements', [])
        if not improvements:
            print(f"  ℹ️  No specific improvements suggested")
            return False
        
        print(f"  💡 Found {len(improvements)} improvement(s)")
        print(f"  📊 Score: {analysis.get('overall_score', 'N/A')}/100")
        print(f"  📝 Summary: {analysis.get('summary', 'N/A')}")
        
        # Ask for confirmation (in interactive mode)
        if os.isatty(sys.stdin.fileno()):
            response = input(f"  Apply {len(improvements)} improvement(s)? [y/N]: ")
            if response.lower() != 'y':
                print(f"  ⏭️  Skipped")
                return False
        
        applied = self._apply_improvements(filepath, improvements)
        
        if applied > 0:
            # Log improvement
            self.improvements_log.setdefault('improvements', []).append({
                'file': rel_path,
                'timestamp': datetime.now().isoformat(),
                'improvements_applied': applied,
                'score_before': analysis.get('overall_score', 'N/A'),
                'summary': analysis.get('summary', '')
            })
            self.stats['files_improved'] += 1
            self.stats['improvements_applied'] += applied
            print(f"  ✅ Applied {applied} improvement(s)")
            return True
        
        return False
    
    def run_once(self, max_files: Optional[int] = None, force: bool = False, skip_lock: bool = False):
        """Run one improvement cycle.
        
        Args:
            max_files: Maximum number of files to process
            force: If True, force remove existing lock file
            skip_lock: If True, skip lock acquisition (for use within run_continuous)
        """
        # Acquire lock (unless called from run_continuous which already has the lock)
        if not skip_lock:
            if not self._acquire_lock(force=force):
                return False
        
        try:
            print("=" * 70)
            print("🔧 Code Improvement Cycle")
            print("=" * 70)
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"PID: {os.getpid()}")
            print()
            
            # Check Ollama connection
            if not self.client.check_server():
                print("❌ Ollama server is not running!")
                print("   Start it with: ollama serve")
                return False
            
            files = self._get_python_files()
            print(f"📁 Found {len(files)} Python file(s)")
            
            if max_files:
                files = files[:max_files]
                print(f"🔢 Processing first {len(files)} file(s)")
            
            self.stats['files_analyzed'] = len(files)
            self.total_files = len(files)
            self.current_file_index = 0
            
            cycle_start = time.time()
            for filepath in files:
                self.improve_file(filepath)
            
            cycle_elapsed = time.time() - cycle_start
            print(f"\n⏱️  Cycle completed in {cycle_elapsed:.1f}s")
        finally:
            # Only release lock if we acquired it
            if not skip_lock:
                self._release_lock()
        
        # Save log
        self._save_improvements_log()
        
        # Print stats
        print("\n" + "=" * 70)
        print("📊 Statistics")
        print("=" * 70)
        print(f"Files analyzed: {self.stats['files_analyzed']}")
        print(f"Files improved: {self.stats['files_improved']}")
        print(f"Improvements applied: {self.stats['improvements_applied']}")
        print("=" * 70)
        
        return True
    
    def run_continuous(self, max_files: Optional[int] = None, force: bool = False):
        """Run continuously, improving code periodically.
        
        Args:
            max_files: Maximum number of files to process per cycle
            force: If True, force remove existing lock file
        """
        # Acquire lock for continuous mode
        if not self._acquire_lock(force=force):
            return
        
        try:
            print("=" * 70)
            print("🚀 Starting Continuous Code Improvement")
            print("=" * 70)
            print(f"Interval: {self.interval} seconds")
            print(f"Model: {self.model or 'auto-select'}")
            print(f"PID: {os.getpid()}")
            print("Press Ctrl+C to stop")
            print("=" * 70)
            print()
            
            cycle = 0
            try:
                while True:
                    cycle += 1
                    print(f"\n🔄 Cycle #{cycle}")
                    # Skip lock acquisition since we already have the lock
                    cycle_success = self.run_once(max_files=max_files, skip_lock=True)
                    
                    if not cycle_success:
                        print("⚠️  Cycle failed, but continuing...")
                    
                    if cycle > 0:
                        print(f"\n⏳ Waiting {self.interval} seconds until next cycle...")
                        # Show countdown
                        for remaining in range(self.interval, 0, -10):
                            if remaining > 10:
                                print(f"   {remaining}s remaining...", end='\r')
                                time.sleep(10)
                            else:
                                time.sleep(remaining)
                                break
                        print("   Starting next cycle...")
                        
            except KeyboardInterrupt:
                print("\n\n🛑 Stopped by user")
                print(f"Total cycles: {cycle}")
                print(f"Total improvements: {self.stats['improvements_applied']}")
        finally:
            self._release_lock()


def main():
    parser = argparse.ArgumentParser(
        description='Continuously improve code using Ollama',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once, improve up to 5 files
  python3 scripts/improve-code.py --once --max-files 5
  
  # Run continuously every 5 minutes
  python3 scripts/improve-code.py --interval 300
  
  # Use specific model
  python3 scripts/improve-code.py --model codellama --once
        """
    )
    parser.add_argument('--once', action='store_true',
                       help='Run once instead of continuously')
    parser.add_argument('--interval', type=int, default=300,
                       help='Seconds between cycles (default: 300)')
    parser.add_argument('--model', type=str, default=None,
                       help='Ollama model to use (default: auto-select)')
    parser.add_argument('--max-files', type=int, default=None,
                       help='Maximum files to process per cycle')
    parser.add_argument('--force', action='store_true',
                       help='Force remove existing lock file if present')
    
    args = parser.parse_args()
    
    improver = CodeImprover(model=args.model, interval=args.interval)
    
    if args.once:
        improver.run_once(max_files=args.max_files, force=args.force)
    else:
        improver.run_continuous(max_files=args.max_files, force=args.force)


if __name__ == '__main__':
    main()
