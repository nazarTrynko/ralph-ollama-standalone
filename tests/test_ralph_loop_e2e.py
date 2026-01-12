#!/usr/bin/env python3
"""
End-to-End Tests for Ralph Loop UI
Tests the complete Ralph Loop flow including project initialization, phase execution, and file tracking.
"""

import sys
import time
import json
import requests
import subprocess
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from lib.path_utils import setup_paths
setup_paths()

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class RalphLoopE2ETestRunner:
    """End-to-end test runner for Ralph Loop functionality."""
    
    def __init__(self, base_url: str = "http://localhost:5001", timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.server_process: Optional[subprocess.Popen] = None
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'tests': []
        }
        self.test_project_path = project_root / 'test_projects'
        self.test_project_path.mkdir(exist_ok=True)
    
    def log(self, message: str, color: str = RESET):
        """Print colored log message."""
        print(f"{color}{message}{RESET}")
    
    def test_pass(self, test_name: str):
        """Record a passing test."""
        self.results['passed'] += 1
        self.results['tests'].append({'name': test_name, 'status': 'PASS'})
        self.log(f"  ✅ {test_name}", GREEN)
    
    def test_fail(self, test_name: str, error: str = ""):
        """Record a failing test."""
        self.results['failed'] += 1
        self.results['tests'].append({'name': test_name, 'status': 'FAIL', 'error': error})
        self.log(f"  ❌ {test_name}", RED)
        if error:
            self.log(f"     Error: {error}", RED)
    
    def test_warn(self, test_name: str, message: str = ""):
        """Record a warning."""
        self.results['warnings'] += 1
        self.results['tests'].append({'name': test_name, 'status': 'WARN', 'message': message})
        self.log(f"  ⚠️  {test_name}", YELLOW)
        if message:
            self.log(f"     {message}", YELLOW)
    
    def cleanup_test_projects(self):
        """Clean up test projects."""
        if self.test_project_path.exists():
            for project_dir in self.test_project_path.iterdir():
                if project_dir.is_dir():
                    try:
                        shutil.rmtree(project_dir)
                    except Exception as e:
                        self.log(f"  ⚠️  Could not remove {project_dir}: {e}", YELLOW)
    
    def test_ralph_start_endpoint(self) -> bool:
        """Test starting a Ralph loop."""
        self.log("\n🚀 Testing /api/ralph/start endpoint...", BLUE)
        
        test_cases = [
            {
                'name': 'Start with phase-by-phase mode',
                'data': {
                    'project_name': 'TestProject1',
                    'description': 'A test project for e2e testing',
                    'initial_task': 'Create a simple hello world script',
                    'mode': 'phase_by_phase'
                }
            },
            {
                'name': 'Start with non-stop mode',
                'data': {
                    'project_name': 'TestProject2',
                    'description': 'Another test project',
                    'initial_task': 'Create a README file',
                    'mode': 'non_stop'
                }
            }
        ]
        
        session_ids = []
        all_passed = True
        
        for test_case in test_cases:
            try:
                self.log(f"  Testing: {test_case['name']}...", BLUE)
                response = requests.post(
                    f"{self.base_url}/api/ralph/start",
                    json=test_case['data'],
                    headers={'Content-Type': 'application/json'},
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('error', f"HTTP {response.status_code}")
                    self.test_fail(f"Start - {test_case['name']}", error_msg)
                    all_passed = False
                    continue
                
                data = response.json()
                
                # Check response structure
                required_fields = ['success', 'session_id', 'project_path', 'mode']
                for field in required_fields:
                    if field not in data:
                        self.test_fail(f"Start - {test_case['name']} structure", 
                                     f"Missing '{field}' field")
                        all_passed = False
                        break
                else:
                    if data.get('success'):
                        self.test_pass(f"Start - {test_case['name']}")
                        session_ids.append(data['session_id'])
                        self.log(f"    Session ID: {data['session_id']}", GREEN)
                        self.log(f"    Project Path: {data['project_path']}", GREEN)
                        self.log(f"    Mode: {data['mode']}", GREEN)
                    else:
                        self.test_fail(f"Start - {test_case['name']}", 
                                     data.get('error', 'Unknown error'))
                        all_passed = False
                        
            except Exception as e:
                self.test_fail(f"Start - {test_case['name']}", str(e))
                all_passed = False
        
        return all_passed, session_ids[0] if session_ids else None
    
    def test_ralph_status_endpoint(self, session_id: Optional[str] = None) -> bool:
        """Test getting Ralph loop status."""
        self.log("\n📊 Testing /api/ralph/status endpoint...", BLUE)
        
        if not session_id:
            self.test_warn("Status endpoint", "No session ID available, skipping")
            return True
        
        try:
            response = requests.get(
                f"{self.base_url}/api/ralph/status",
                params={'session_id': session_id},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error', f"HTTP {response.status_code}")
                self.test_fail("Status endpoint", error_msg)
                return False
            
            data = response.json()
            
            if not data.get('success'):
                self.test_fail("Status endpoint", data.get('error', 'Unknown error'))
                return False
            
            status = data.get('status', {})
            
            # Check required status fields
            required_fields = ['is_running', 'is_paused', 'mode', 'current_phase', 'status_log']
            for field in required_fields:
                if field not in status:
                    self.test_fail(f"Status - {field} missing", "")
                    return False
            
            self.test_pass("Status endpoint structure")
            self.log(f"    Running: {status.get('is_running')}", GREEN)
            self.log(f"    Paused: {status.get('is_paused')}", GREEN)
            self.log(f"    Mode: {status.get('mode')}", GREEN)
            self.log(f"    Phase: {status.get('current_phase')}", GREEN)
            
            return True
            
        except Exception as e:
            self.test_fail("Status endpoint", str(e))
            return False
    
    def test_ralph_pause_resume(self, session_id: Optional[str] = None) -> bool:
        """Test pausing and resuming a Ralph loop."""
        self.log("\n⏸️  Testing pause/resume functionality...", BLUE)
        
        if not session_id:
            self.test_warn("Pause/Resume", "No session ID available, skipping")
            return True
        
        try:
            # Test pause
            self.log("  Testing pause...", BLUE)
            response = requests.post(
                f"{self.base_url}/api/ralph/pause",
                json={'session_id': session_id},
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error', f"HTTP {response.status_code}")
                self.test_fail("Pause", error_msg)
                return False
            
            data = response.json()
            if data.get('success'):
                self.test_pass("Pause")
                time.sleep(1)  # Wait a bit
            else:
                self.test_fail("Pause", data.get('error', 'Unknown error'))
                return False
            
            # Test resume
            self.log("  Testing resume...", BLUE)
            response = requests.post(
                f"{self.base_url}/api/ralph/resume",
                json={'session_id': session_id, 'user_input': 'Test input'},
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error', f"HTTP {response.status_code}")
                self.test_fail("Resume", error_msg)
                return False
            
            data = response.json()
            if data.get('success'):
                self.test_pass("Resume")
            else:
                self.test_fail("Resume", data.get('error', 'Unknown error'))
                return False
            
            return True
            
        except Exception as e:
            self.test_fail("Pause/Resume", str(e))
            return False
    
    def test_ralph_mode_switch(self, session_id: Optional[str] = None) -> bool:
        """Test switching between modes."""
        self.log("\n🔄 Testing mode switching...", BLUE)
        
        if not session_id:
            self.test_warn("Mode switch", "No session ID available, skipping")
            return True
        
        try:
            # Get current mode
            response = requests.get(
                f"{self.base_url}/api/ralph/status",
                params={'session_id': session_id},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                self.test_fail("Mode switch - get status", "Could not get current status")
                return False
            
            data = response.json()
            if not data.get('success'):
                self.test_fail("Mode switch - get status", data.get('error', 'Unknown error'))
                return False
            
            current_mode = data['status'].get('mode', 'phase_by_phase')
            new_mode = 'non_stop' if current_mode == 'phase_by_phase' else 'phase_by_phase'
            
            # Switch mode
            response = requests.post(
                f"{self.base_url}/api/ralph/mode",
                json={'session_id': session_id, 'mode': new_mode},
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error', f"HTTP {response.status_code}")
                self.test_fail("Mode switch", error_msg)
                return False
            
            data = response.json()
            if data.get('success') and data.get('mode') == new_mode:
                self.test_pass(f"Mode switch ({current_mode} → {new_mode})")
            else:
                self.test_fail("Mode switch", data.get('error', 'Mode not changed'))
                return False
            
            return True
            
        except Exception as e:
            self.test_fail("Mode switch", str(e))
            return False
    
    def test_ralph_files_endpoint(self, session_id: Optional[str] = None) -> bool:
        """Test getting file list."""
        self.log("\n📁 Testing /api/ralph/files endpoint...", BLUE)
        
        if not session_id:
            self.test_warn("Files endpoint", "No session ID available, skipping")
            return True
        
        try:
            response = requests.get(
                f"{self.base_url}/api/ralph/files",
                params={'session_id': session_id},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error', f"HTTP {response.status_code}")
                self.test_fail("Files endpoint", error_msg)
                return False
            
            data = response.json()
            
            if not data.get('success'):
                self.test_fail("Files endpoint", data.get('error', 'Unknown error'))
                return False
            
            # Check response structure
            if 'files' in data and 'changes' in data:
                self.test_pass("Files endpoint structure")
                files = data.get('files', [])
                changes = data.get('changes', {})
                self.log(f"    Files tracked: {len(files)}", GREEN)
                self.log(f"    Created: {len(changes.get('created', []))}", GREEN)
                self.log(f"    Modified: {len(changes.get('modified', []))}", GREEN)
                self.log(f"    Deleted: {len(changes.get('deleted', []))}", GREEN)
            else:
                self.test_fail("Files endpoint structure", "Missing 'files' or 'changes' field")
                return False
            
            return True
            
        except Exception as e:
            self.test_fail("Files endpoint", str(e))
            return False
    
    def test_ralph_stop_endpoint(self, session_id: Optional[str] = None) -> bool:
        """Test stopping a Ralph loop."""
        self.log("\n🛑 Testing /api/ralph/stop endpoint...", BLUE)
        
        if not session_id:
            self.test_warn("Stop endpoint", "No session ID available, skipping")
            return True
        
        try:
            response = requests.post(
                f"{self.base_url}/api/ralph/stop",
                json={'session_id': session_id},
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get('error', f"HTTP {response.status_code}")
                self.test_fail("Stop endpoint", error_msg)
                return False
            
            data = response.json()
            if data.get('success'):
                self.test_pass("Stop endpoint")
            else:
                self.test_fail("Stop endpoint", data.get('error', 'Unknown error'))
                return False
            
            return True
            
        except Exception as e:
            self.test_fail("Stop endpoint", str(e))
            return False
    
    def test_ralph_error_handling(self) -> bool:
        """Test error handling for Ralph endpoints."""
        self.log("\n⚠️  Testing error handling...", BLUE)
        
        test_cases = [
            {
                'name': 'Start without project name',
                'endpoint': '/api/ralph/start',
                'method': 'POST',
                'data': {'description': 'Test'},
                'expected_status': 400
            },
            {
                'name': 'Status without session_id',
                'endpoint': '/api/ralph/status',
                'method': 'GET',
                'params': {},
                'expected_status': 400
            },
            {
                'name': 'Status with invalid session_id',
                'endpoint': '/api/ralph/status',
                'method': 'GET',
                'params': {'session_id': 'invalid_session_12345'},
                'expected_status': 404
            },
            {
                'name': 'Pause without session_id',
                'endpoint': '/api/ralph/pause',
                'method': 'POST',
                'data': {},
                'expected_status': 400
            },
            {
                'name': 'Resume without session_id',
                'endpoint': '/api/ralph/resume',
                'method': 'POST',
                'data': {},
                'expected_status': 400
            },
            {
                'name': 'Stop without session_id',
                'endpoint': '/api/ralph/stop',
                'method': 'POST',
                'data': {},
                'expected_status': 400
            },
            {
                'name': 'Mode switch without session_id',
                'endpoint': '/api/ralph/mode',
                'method': 'POST',
                'data': {},
                'expected_status': 400
            },
            {
                'name': 'Files without session_id',
                'endpoint': '/api/ralph/files',
                'method': 'GET',
                'params': {},
                'expected_status': 400
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            try:
                self.log(f"  Testing: {test_case['name']}...", BLUE)
                
                method = test_case.get('method', 'POST')
                if method == 'GET':
                    response = requests.get(
                        f"{self.base_url}{test_case['endpoint']}",
                        params=test_case.get('params', {}),
                        timeout=self.timeout
                    )
                else:
                    response = requests.post(
                        f"{self.base_url}{test_case['endpoint']}",
                        json=test_case.get('data', {}),
                        headers={'Content-Type': 'application/json'},
                        timeout=self.timeout
                    )
                
                if response.status_code == test_case['expected_status']:
                    self.test_pass(f"Error handling - {test_case['name']}")
                else:
                    self.test_fail(f"Error handling - {test_case['name']}", 
                                 f"Expected {test_case['expected_status']}, got {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.test_fail(f"Error handling - {test_case['name']}", str(e))
                all_passed = False
        
        return all_passed
    
    def test_ralph_project_initialization(self, session_id: Optional[str] = None) -> bool:
        """Test that project was initialized correctly."""
        self.log("\n📂 Testing project initialization...", BLUE)
        
        if not session_id:
            self.test_warn("Project initialization", "No session ID available, skipping")
            return True
        
        try:
            # Get status to find project path
            response = requests.get(
                f"{self.base_url}/api/ralph/status",
                params={'session_id': session_id},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                self.test_fail("Project initialization - get status", "Could not get status")
                return False
            
            data = response.json()
            if not data.get('success'):
                self.test_fail("Project initialization - get status", data.get('error', 'Unknown error'))
                return False
            
            # Try to find project path from files
            files_response = requests.get(
                f"{self.base_url}/api/ralph/files",
                params={'session_id': session_id},
                timeout=self.timeout
            )
            
            if files_response.status_code == 200:
                files_data = files_response.json()
                if files_data.get('success'):
                    files = files_data.get('files', [])
                    # Check for expected files
                    expected_files = ['README.md', '@fix_plan.md']
                    found_files = [f['path'] for f in files]
                    
                    for expected in expected_files:
                        if any(expected in f for f in found_files):
                            self.test_pass(f"Project initialization - {expected} exists")
                        else:
                            self.test_warn(f"Project initialization - {expected} not found", 
                                         "File may not have been created yet")
            
            return True
            
        except Exception as e:
            self.test_fail("Project initialization", str(e))
            return False
    
    def run_all_tests(self, start_server: bool = True) -> int:
        """Run all Ralph Loop e2e tests."""
        self.log("=" * 70, BLUE)
        self.log("🧪 Ralph Loop UI - End-to-End Tests", BLUE)
        self.log("=" * 70, BLUE)
        
        try:
            # Clean up any existing test projects
            self.cleanup_test_projects()
            
            # Start server if requested
            if start_server:
                self.log("\n🚀 Starting Flask server...", BLUE)
                try:
                    self.server_process = subprocess.Popen(
                        [sys.executable, str(project_root / 'ui' / 'app.py')],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=str(project_root)
                    )
                    
                    # Wait for server to start
                    max_attempts = 10
                    for i in range(max_attempts):
                        try:
                            response = requests.get(f"{self.base_url}/", timeout=2)
                            if response.status_code == 200:
                                self.log("  ✅ Server started successfully", GREEN)
                                break
                        except requests.exceptions.RequestException:
                            time.sleep(1)
                            continue
                    else:
                        self.test_fail("Server startup", "Server did not respond within timeout")
                        return 1
                    
                    time.sleep(2)  # Give server time to fully start
                except Exception as e:
                    self.test_fail("Server startup", str(e))
                    return 1
            
            # Run tests
            session_id = None
            passed, session_id = self.test_ralph_start_endpoint()
            if not passed:
                self.log("  ⚠️  Some start tests failed, continuing with available session...", YELLOW)
            
            if session_id:
                time.sleep(2)  # Give loop time to start
                self.test_ralph_status_endpoint(session_id)
                self.test_ralph_project_initialization(session_id)
                self.test_ralph_files_endpoint(session_id)
                self.test_ralph_pause_resume(session_id)
                self.test_ralph_mode_switch(session_id)
                # Stop at the end
                self.test_ralph_stop_endpoint(session_id)
            else:
                self.test_warn("Ralph Loop tests", "No session ID available, some tests skipped")
            
            # Error handling tests don't need a session
            self.test_ralph_error_handling()
            
            # Print summary
            self.print_summary()
            
            # Cleanup
            self.cleanup_test_projects()
            
            return 0 if self.results['failed'] == 0 else 1
            
        except KeyboardInterrupt:
            self.log("\n\n⚠️  Tests interrupted by user", YELLOW)
            return 1
        except Exception as e:
            self.log(f"\n\n❌ Unexpected error: {e}", RED)
            import traceback
            traceback.print_exc()
            return 1
        finally:
            if start_server and self.server_process:
                self.log("\n🛑 Stopping Flask server...", BLUE)
                try:
                    self.server_process.terminate()
                    self.server_process.wait(timeout=5)
                    self.log("  ✅ Server stopped", GREEN)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                    self.log("  ⚠️  Server force-killed", YELLOW)
                except Exception as e:
                    self.log(f"  ⚠️  Error stopping server: {e}", YELLOW)
            
            self.cleanup_test_projects()
    
    def generate_junit_xml(self, output_path: str) -> None:
        """Generate JUnit XML report.
        
        Args:
            output_path: Path to write JUnit XML file
        """
        testsuite = ET.Element('testsuite')
        testsuite.set('name', 'Ralph Loop E2E Tests')
        testsuite.set('tests', str(len(self.results['tests'])))
        testsuite.set('failures', str(self.results['failed']))
        testsuite.set('errors', '0')
        testsuite.set('time', '0')
        testsuite.set('timestamp', datetime.now().isoformat())
        
        for test in self.results['tests']:
            testcase = ET.SubElement(testsuite, 'testcase')
            testcase.set('name', test['name'])
            testcase.set('classname', 'RalphLoopE2ETestRunner')
            
            if test['status'] == 'FAIL':
                failure = ET.SubElement(testcase, 'failure')
                failure.set('message', test.get('error', 'Test failed'))
                failure.text = test.get('error', '')
            elif test['status'] == 'WARN':
                skipped = ET.SubElement(testcase, 'skipped')
                skipped.set('message', test.get('message', 'Warning'))
        
        tree = ET.ElementTree(testsuite)
        ET.indent(tree, space='  ')
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    def print_summary(self):
        """Print test summary."""
        self.log("\n" + "=" * 70, BLUE)
        self.log("📊 Test Summary", BLUE)
        self.log("=" * 70, BLUE)
        
        total = self.results['passed'] + self.results['failed'] + self.results['warnings']
        
        self.log(f"\nTotal tests: {total}", BLUE)
        self.log(f"✅ Passed: {self.results['passed']}", GREEN)
        self.log(f"❌ Failed: {self.results['failed']}", RED if self.results['failed'] > 0 else RESET)
        self.log(f"⚠️  Warnings: {self.results['warnings']}", YELLOW if self.results['warnings'] > 0 else RESET)
        
        if self.results['failed'] > 0:
            self.log("\n❌ Failed Tests:", RED)
            for test in self.results['tests']:
                if test['status'] == 'FAIL':
                    self.log(f"  - {test['name']}", RED)
                    if 'error' in test:
                        self.log(f"    {test['error']}", RED)
        
        if self.results['warnings'] > 0:
            self.log("\n⚠️  Warnings:", YELLOW)
            for test in self.results['tests']:
                if test['status'] == 'WARN':
                    self.log(f"  - {test['name']}", YELLOW)
                    if 'message' in test:
                        self.log(f"    {test['message']}", YELLOW)
        
        self.log("\n" + "=" * 70, BLUE)
        
        if self.results['failed'] == 0:
            self.log("✅ All critical tests passed!", GREEN)
        else:
            self.log("❌ Some tests failed. Check errors above.", RED)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='E2E tests for Ralph Loop UI')
    parser.add_argument('--url', default='http://localhost:5001',
                       help='Base URL of the UI server (default: http://localhost:5001)')
    parser.add_argument('--no-start-server', action='store_true',
                       help='Assume server is already running')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    parser.add_argument('--junit-xml', type=str, default=None,
                       help='Path to write JUnit XML report (optional)')
    
    args = parser.parse_args()
    
    runner = RalphLoopE2ETestRunner(base_url=args.url, timeout=args.timeout)
    exit_code = runner.run_all_tests(start_server=not args.no_start_server)
    
    # Generate JUnit XML if requested
    if args.junit_xml:
        try:
            runner.generate_junit_xml(args.junit_xml)
            print(f"✅ JUnit XML report written to: {args.junit_xml}")
        except Exception as e:
            print(f"⚠️  Failed to generate JUnit XML: {e}", file=sys.stderr)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
