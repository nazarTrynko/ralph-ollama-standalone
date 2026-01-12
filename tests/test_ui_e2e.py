#!/usr/bin/env python3
"""
End-to-End Test for Ralph Ollama UI
Tests the complete UI flow including server, endpoints, and responses.
"""

import sys
import time
import json
import requests
import subprocess
import signal
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


class UITestRunner:
    """End-to-end test runner for the UI."""
    
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
    
    def start_server(self) -> bool:
        """Start the Flask server."""
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
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(1)
                    continue
            
            self.test_fail("Server startup", "Server did not respond within timeout")
            return False
            
        except Exception as e:
            self.test_fail("Server startup", str(e))
            return False
    
    def stop_server(self):
        """Stop the Flask server."""
        if self.server_process:
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
    
    def test_homepage(self) -> bool:
        """Test the homepage loads."""
        self.log("\n📄 Testing homepage...", BLUE)
        try:
            response = requests.get(f"{self.base_url}/", timeout=self.timeout)
            if response.status_code == 200:
                if 'Ralph Ollama' in response.text:
                    self.test_pass("Homepage loads")
                    return True
                else:
                    self.test_fail("Homepage content", "Expected 'Ralph Ollama' not found")
                    return False
            else:
                self.test_fail("Homepage status", f"Expected 200, got {response.status_code}")
                return False
        except Exception as e:
            self.test_fail("Homepage request", str(e))
            return False
    
    def test_status_endpoint(self) -> bool:
        """Test the /api/status endpoint."""
        self.log("\n📊 Testing /api/status endpoint...", BLUE)
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=self.timeout)
            
            if response.status_code != 200:
                self.test_fail("Status endpoint status", f"Expected 200, got {response.status_code}")
                return False
            
            data = response.json()
            
            # Check required fields
            required_fields = ['connected', 'server_url', 'default_model', 'models', 'adapter_available']
            for field in required_fields:
                if field not in data:
                    self.test_fail(f"Status endpoint - {field} missing", "")
                    return False
            
            self.test_pass("Status endpoint structure")
            
            # Log status info
            if data.get('connected'):
                self.log(f"  📡 Ollama server: Connected ({data.get('server_url')})", GREEN)
                self.log(f"  🤖 Default model: {data.get('default_model')}", GREEN)
                models = data.get('models', [])
                if models:
                    self.log(f"  📦 Available models: {len(models)}", GREEN)
                else:
                    self.test_warn("No models available", "Pull a model with: ollama pull llama3.2")
            else:
                self.test_warn("Ollama server not connected", 
                             "Start Ollama with: ollama serve")
            
            return True
            
        except Exception as e:
            self.test_fail("Status endpoint request", str(e))
            return False
    
    def test_models_endpoint(self) -> bool:
        """Test the /api/models endpoint."""
        self.log("\n📦 Testing /api/models endpoint...", BLUE)
        try:
            response = requests.get(f"{self.base_url}/api/models", timeout=self.timeout)
            
            if response.status_code == 503:
                self.test_warn("Models endpoint", "Ollama server not running")
                return True  # This is OK if Ollama isn't running
            
            if response.status_code != 200:
                self.test_fail("Models endpoint status", f"Expected 200, got {response.status_code}")
                return False
            
            data = response.json()
            
            if 'models' in data:
                self.test_pass("Models endpoint")
                models = data.get('models', [])
                if models:
                    self.log(f"  📋 Found {len(models)} model(s): {', '.join(models[:5])}", GREEN)
                else:
                    self.test_warn("No models returned", "")
                return True
            else:
                self.test_fail("Models endpoint structure", "Missing 'models' field")
                return False
                
        except Exception as e:
            self.test_fail("Models endpoint request", str(e))
            return False
    
    def test_generate_endpoint(self) -> bool:
        """Test the /api/generate endpoint."""
        self.log("\n💬 Testing /api/generate endpoint...", BLUE)
        
        test_cases = [
            {
                'name': 'Simple prompt',
                'data': {
                    'prompt': 'Say hello in exactly one word.',
                    'model': None,
                    'task_type': None
                }
            },
            {
                'name': 'Prompt with task type',
                'data': {
                    'prompt': 'Write a Python function to add two numbers.',
                    'model': None,
                    'task_type': 'implementation'
                }
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            try:
                self.log(f"  Testing: {test_case['name']}...", BLUE)
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=test_case['data'],
                    headers={'Content-Type': 'application/json'},
                    timeout=60  # Longer timeout for generation
                )
                
                if response.status_code == 503:
                    self.test_warn(f"Generate - {test_case['name']}", 
                                 "Ollama server not running")
                    continue
                
                if response.status_code != 200:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('error', f"HTTP {response.status_code}")
                    self.test_fail(f"Generate - {test_case['name']}", error_msg)
                    all_passed = False
                    continue
                
                data = response.json()
                
                # Check response structure
                if 'success' not in data:
                    self.test_fail(f"Generate - {test_case['name']} structure", 
                                 "Missing 'success' field")
                    all_passed = False
                    continue
                
                if not data.get('success'):
                    error_msg = data.get('error', 'Unknown error')
                    self.test_fail(f"Generate - {test_case['name']}", error_msg)
                    all_passed = False
                    continue
                
                # Check response content
                if 'response' in data and data['response']:
                    response_text = data['response']
                    self.test_pass(f"Generate - {test_case['name']}")
                    self.log(f"    Response preview: {response_text[:100]}...", GREEN)
                    
                    # Check metadata
                    if 'model' in data:
                        self.log(f"    Model used: {data['model']}", GREEN)
                    if 'tokens' in data:
                        tokens = data['tokens']
                        if isinstance(tokens, dict) and 'total' in tokens:
                            self.log(f"    Tokens: {tokens['total']} total", GREEN)
                else:
                    self.test_fail(f"Generate - {test_case['name']}", 
                                 "Empty or missing response")
                    all_passed = False
                    
            except requests.exceptions.Timeout:
                self.test_fail(f"Generate - {test_case['name']}", "Request timeout")
                all_passed = False
            except Exception as e:
                self.test_fail(f"Generate - {test_case['name']}", str(e))
                all_passed = False
        
        return all_passed
    
    def test_error_handling(self) -> bool:
        """Test error handling."""
        self.log("\n⚠️  Testing error handling...", BLUE)
        
        # Test missing prompt
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={},  # Empty request
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code == 400:
                data = response.json()
                if 'error' in data and 'prompt' in data.get('error', '').lower():
                    self.test_pass("Error handling - missing prompt")
                else:
                    self.test_fail("Error handling - missing prompt", 
                                 "Wrong error message")
                    return False
            else:
                self.test_fail("Error handling - missing prompt", 
                             f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.test_fail("Error handling - missing prompt", str(e))
            return False
        
        # Test invalid JSON
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                data="not json",
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            # Should handle gracefully
            if response.status_code in [400, 500]:
                self.test_pass("Error handling - invalid JSON")
            else:
                self.test_warn("Error handling - invalid JSON", 
                             f"Unexpected status: {response.status_code}")
                
        except Exception as e:
            self.test_warn("Error handling - invalid JSON", str(e))
        
        return True
    
    def run_all_tests(self, start_server: bool = True) -> int:
        """Run all tests."""
        self.log("=" * 70, BLUE)
        self.log("🧪 Ralph Ollama UI - End-to-End Tests", BLUE)
        self.log("=" * 70, BLUE)
        
        try:
            # Start server if requested
            if start_server:
                if not self.start_server():
                    self.log("\n❌ Failed to start server. Cannot continue.", RED)
                    return 1
                time.sleep(2)  # Give server time to fully start
            
            # Run tests
            self.test_homepage()
            self.test_status_endpoint()
            self.test_models_endpoint()
            self.test_error_handling()
            self.test_generate_endpoint()
            
            # Print summary
            self.print_summary()
            
            return 0 if self.results['failed'] == 0 else 1
            
        finally:
            if start_server:
                self.stop_server()
    
    def generate_junit_xml(self, output_path: str) -> None:
        """Generate JUnit XML report.
        
        Args:
            output_path: Path to write JUnit XML file
        """
        testsuite = ET.Element('testsuite')
        testsuite.set('name', 'UI E2E Tests')
        testsuite.set('tests', str(len(self.results['tests'])))
        testsuite.set('failures', str(self.results['failed']))
        testsuite.set('errors', '0')
        testsuite.set('time', '0')
        testsuite.set('timestamp', datetime.now().isoformat())
        
        for test in self.results['tests']:
            testcase = ET.SubElement(testsuite, 'testcase')
            testcase.set('name', test['name'])
            testcase.set('classname', 'UITestRunner')
            
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
    
    parser = argparse.ArgumentParser(description='E2E tests for Ralph Ollama UI')
    parser.add_argument('--url', default='http://localhost:5001',
                       help='Base URL of the UI server (default: http://localhost:5001)')
    parser.add_argument('--no-start-server', action='store_true',
                       help='Assume server is already running')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    parser.add_argument('--junit-xml', type=str, default=None,
                       help='Path to write JUnit XML report (optional)')
    
    args = parser.parse_args()
    
    runner = UITestRunner(base_url=args.url, timeout=args.timeout)
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
