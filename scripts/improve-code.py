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
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse

# Add project root to path to enable package imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from lib.ollama_client import OllamaClient
from integration.ralph_ollama_adapter import RalphOllamaAdapter

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
IMPROVEMENT_LOG = PROJECT_ROOT / 'state' / 'improvements.json'
EXCLUDE_DIRS = {'.git', '__pycache__', 'venv', 'node_modules', '.cursor', 'state'}
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
        self.model = model
        self.interval = interval
        self.improvements_log = self._load_improvements_log()
        self.stats = {
            'files_analyzed': 0,
            'files_improved': 0,
            'improvements_applied': 0,
            'start_time': datetime.now().isoformat()
        }
        
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
            
            for filename in filenames:
                filepath = Path(root) / filename
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
            
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                analysis = json.loads(json_str)
                return analysis
            else:
                print(f"  ⚠️  Could not parse JSON from response for {filepath.name}")
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
        print(f"\n📄 Analyzing: {rel_path}")
        
        analysis = self._analyze_code(filepath)
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
    
    def run_once(self, max_files: Optional[int] = None):
        """Run one improvement cycle."""
        print("=" * 70)
        print("🔧 Code Improvement Cycle")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
        
        for filepath in files:
            self.improve_file(filepath)
        
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
    
    def run_continuous(self, max_files: Optional[int] = None):
        """Run continuously, improving code periodically."""
        print("=" * 70)
        print("🚀 Starting Continuous Code Improvement")
        print("=" * 70)
        print(f"Interval: {self.interval} seconds")
        print(f"Model: {self.model or 'auto-select'}")
        print("Press Ctrl+C to stop")
        print("=" * 70)
        print()
        
        cycle = 0
        try:
            while True:
                cycle += 1
                print(f"\n🔄 Cycle #{cycle}")
                self.run_once(max_files=max_files)
                
                if cycle > 0:
                    print(f"\n⏳ Waiting {self.interval} seconds until next cycle...")
                    time.sleep(self.interval)
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user")
            print(f"Total cycles: {cycle}")
            print(f"Total improvements: {self.stats['improvements_applied']}")


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
    
    args = parser.parse_args()
    
    improver = CodeImprover(model=args.model, interval=args.interval)
    
    if args.once:
        improver.run_once(max_files=args.max_files)
    else:
        improver.run_continuous(max_files=args.max_files)


if __name__ == '__main__':
    main()
