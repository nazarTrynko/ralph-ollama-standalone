#!/usr/bin/env python3
"""
Code Validator and Executor
Validates and executes generated code safely.
"""

import ast
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from lib.logging_config import get_logger

logger = get_logger('code_validator')


class CodeValidator:
    """Validate and execute code safely."""
    
    def __init__(self, project_path: Path, timeout: int = 30):
        """Initialize code validator.
        
        Args:
            project_path: Path to the project directory
            timeout: Execution timeout in seconds
        """
        self.project_path = Path(project_path).resolve()
        self.timeout = timeout
    
    def validate_python_syntax(self, code: str, file_path: str = "unknown") -> Tuple[bool, Optional[str]]:
        """Validate Python syntax.
        
        Args:
            code: Python code to validate
            file_path: Path to the file (for error messages)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            error_msg = f"Syntax error in {file_path} at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\n  {e.text.strip()}"
                if e.offset:
                    error_msg += f"\n  {' ' * (e.offset - 1)}^"
            return False, error_msg
        except Exception as e:
            return False, f"Error parsing {file_path}: {str(e)}"
    
    def validate_file(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Validate a file before writing.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_path': str(file_path)
        }
        
        # Check file extension
        ext = file_path.suffix.lower()
        
        # Check for common issues
        if not content.strip():
            result['warnings'].append("File is empty")
            return result
        
        # Validate based on file extension
        if ext == '.py':
            # Only validate Python syntax for .py files
            is_valid, error = self.validate_python_syntax(content, str(file_path))
            if not is_valid:
                result['valid'] = False
                result['errors'].append(error)
        elif ext == '.json':
            # Validate JSON syntax
            is_valid, error = self.validate_json_syntax(content, str(file_path))
            if not is_valid:
                result['valid'] = False
                result['errors'].append(error)
        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            # JavaScript/TypeScript files - skip validation for now
            # Could add node/eslint validation in the future if available
            pass
        elif ext in ['.html', '.css', '.md', '.txt', '.sh']:
            # Text-based files - no syntax validation needed
            pass
        else:
            # Unknown extension - check if content looks like Python (might be misnamed)
            if any(keyword in content.lower() for keyword in ['def ', 'import ', 'from ', 'class ']):
                if 'const ' not in content.lower() and 'let ' not in content.lower() and 'function ' not in content.lower():
                    result['warnings'].append(f"File has extension {ext} but contains Python-like code")
        
        # Check for suspicious patterns (basic security check) - only for code files
        if ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.sh']:
            suspicious_patterns = [
                ('import os', 'os.system'),
                ('import subprocess', 'subprocess.call'),
                ('import sys', 'sys.exit'),
                ('eval(', 'eval'),
                ('exec(', 'exec'),
                ('__import__', '__import__'),
            ]
            
            for pattern, name in suspicious_patterns:
                if pattern in content:
                    result['warnings'].append(f"Contains potentially unsafe code: {name}")
        
        return result
    
    def validate_json_syntax(self, code: str, file_path: str = "unknown") -> Tuple[bool, Optional[str]]:
        """Validate JSON syntax.
        
        Args:
            code: JSON code to validate
            file_path: Path to the file (for error messages)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            import json
            # Remove single-line comments (//) which some JSON variants allow
            json_content = code
            json_lines = []
            for line in json_content.split('\n'):
                # Remove // comments
                if '//' in line:
                    line = line[:line.index('//')]
                json_lines.append(line)
            json_content = '\n'.join(json_lines)
            
            json.loads(json_content)
            return True, None
        except json.JSONDecodeError as e:
            error_msg = f"JSON syntax error in {file_path} at line {e.lineno}: {e.msg}"
            if e.doc:
                # Show context around error
                lines = e.doc.split('\n')
                if e.lineno <= len(lines):
                    error_msg += f"\n  {lines[e.lineno - 1].strip()}"
            return False, error_msg
        except Exception as e:
            return False, f"Error parsing JSON in {file_path}: {str(e)}"
    
    def execute_python_file(self, file_path: Path, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute a Python file safely.
        
        Args:
            file_path: Path to the Python file to execute
            args: Optional command-line arguments
            
        Returns:
            Execution result dictionary
        """
        result = {
            'success': False,
            'stdout': '',
            'stderr': '',
            'exit_code': None,
            'error': None
        }
        
        if not file_path.exists():
            result['error'] = f"File not found: {file_path}"
            return result
        
        if file_path.suffix != '.py':
            result['error'] = f"Not a Python file: {file_path}"
            return result
        
        try:
            # Execute in project directory
            cmd = [sys.executable, str(file_path)]
            if args:
                cmd.extend(args)
            
            process = subprocess.run(
                cmd,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            result['stdout'] = process.stdout
            result['stderr'] = process.stderr
            result['exit_code'] = process.returncode
            result['success'] = process.returncode == 0
            
            if not result['success']:
                result['error'] = f"Execution failed with exit code {process.returncode}"
                if process.stderr:
                    result['error'] += f": {process.stderr[:200]}"
        
        except subprocess.TimeoutExpired:
            result['error'] = f"Execution timed out after {self.timeout} seconds"
        except Exception as e:
            result['error'] = f"Error executing file: {str(e)}"
        
        return result
    
    def run_tests(self, test_pattern: str = "test_*.py") -> Dict[str, Any]:
        """Run tests in the project.
        
        Args:
            test_pattern: Pattern to match test files
            
        Returns:
            Test execution result dictionary
        """
        result = {
            'success': False,
            'tests_found': False,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'output': '',
            'error': None
        }
        
        # Look for test files
        test_files = list(self.project_path.rglob(test_pattern))
        test_dirs = [
            self.project_path / 'tests',
            self.project_path / 'test',
        ]
        
        # Also check test directories
        for test_dir in test_dirs:
            if test_dir.exists():
                test_files.extend(list(test_dir.rglob(test_pattern)))
        
        if not test_files:
            result['error'] = "No test files found"
            return result
        
        result['tests_found'] = True
        result['tests_run'] = len(test_files)
        
        # Try to run tests with pytest if available
        try:
            process = subprocess.run(
                [sys.executable, '-m', 'pytest', str(self.project_path / 'tests'), '-v'],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=self.timeout * 2  # Tests might take longer
            )
            
            result['output'] = process.stdout + process.stderr
            result['success'] = process.returncode == 0
            
            # Try to parse test results
            if 'passed' in process.stdout.lower():
                # Simple parsing - count passed/failed
                lines = process.stdout.split('\n')
                for line in lines:
                    if 'passed' in line.lower() and 'failed' not in line.lower():
                        # Try to extract number
                        import re
                        match = re.search(r'(\d+)\s+passed', line.lower())
                        if match:
                            result['tests_passed'] = int(match.group(1))
                    if 'failed' in line.lower():
                        match = re.search(r'(\d+)\s+failed', line.lower())
                        if match:
                            result['tests_failed'] = int(match.group(1))
        
        except FileNotFoundError:
            # pytest not available, try unittest
            try:
                process = subprocess.run(
                    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', test_pattern],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout * 2
                )
                
                result['output'] = process.stdout + process.stderr
                result['success'] = process.returncode == 0
            except Exception as e:
                result['error'] = f"Could not run tests: {str(e)}"
        except subprocess.TimeoutExpired:
            result['error'] = f"Test execution timed out after {self.timeout * 2} seconds"
        except Exception as e:
            result['error'] = f"Error running tests: {str(e)}"
        
        return result
    
    def validate_and_execute(self, files: List[Dict[str, str]], execute: bool = False, run_tests: bool = False) -> Dict[str, Any]:
        """Validate multiple files and optionally execute them.
        
        Args:
            files: List of file dictionaries with 'path' and 'content' keys
            execute: Whether to execute Python files
            run_tests: Whether to run tests after execution
            
        Returns:
            Validation and execution results
        """
        results = {
            'validated': [],
            'executed': [],
            'test_results': None,
            'errors': [],
            'warnings': []
        }
        
        # Validate all files
        for file_info in files:
            file_path = self.project_path / file_info['path']
            validation = self.validate_file(file_path, file_info['content'])
            results['validated'].append(validation)
            
            if not validation['valid']:
                results['errors'].extend(validation['errors'])
            if validation['warnings']:
                results['warnings'].extend(validation['warnings'])
        
        # Execute Python files if requested
        if execute:
            for file_info in files:
                file_path = self.project_path / file_info['path']
                if file_path.suffix == '.py' and file_path.exists():
                    exec_result = self.execute_python_file(file_path)
                    results['executed'].append({
                        'file': str(file_path),
                        'result': exec_result
                    })
                    
                    if not exec_result['success']:
                        results['errors'].append(f"Execution failed for {file_path}: {exec_result.get('error', 'Unknown error')}")
        
        # Run tests if requested
        if run_tests:
            test_result = self.run_tests()
            results['test_results'] = test_result
            
            if not test_result['success'] and test_result.get('error'):
                results['warnings'].append(f"Test execution: {test_result['error']}")
        
        return results
