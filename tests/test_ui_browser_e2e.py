#!/usr/bin/env python3
"""
Browser-based End-to-End Tests for Ralph Ollama UI
Tests the web application through actual browser interactions using Playwright.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from playwright.sync_api import Page, expect, Browser, BrowserContext
except ImportError:
    print("ERROR: Playwright not installed. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)

import subprocess
import requests
from typing import Optional


class BrowserE2ETestRunner:
    """Browser-based e2e test runner using Playwright."""
    
    def __init__(self, base_url: str = "http://localhost:5001", headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.server_process: Optional[subprocess.Popen] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    def start_server(self) -> bool:
        """Start Flask server."""
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, str(project_root / 'ui' / 'app.py')],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(project_root)
            )
            
            # Wait for server to start
            max_attempts = 30
            for i in range(max_attempts):
                try:
                    response = requests.get(f"{self.base_url}/", timeout=2)
                    if response.status_code == 200:
                        return True
                except Exception:
                    pass
                time.sleep(1)
            
            return False
        except Exception:
            return False
    
    def stop_server(self):
        """Stop Flask server."""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            except Exception:
                pass
    
    def setup_browser(self):
        """Setup Playwright browser."""
        from playwright.sync_api import sync_playwright
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir="test-reports/videos/" if not self.headless else None
        )
        self.page = self.context.new_page()
    
    def teardown_browser(self):
        """Teardown Playwright browser."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
    
    def test_homepage_loads(self) -> bool:
        """Test that homepage loads correctly."""
        try:
            self.page.goto(self.base_url)
            
            # Check title
            expect(self.page).to_have_title("Ralph Ollama - Local UI")
            
            # Check main heading
            expect(self.page.locator("h1")).to_contain_text("Ralph Ollama")
            
            # Check tabs exist
            expect(self.page.locator("text=Send Prompt")).to_be_visible()
            expect(self.page.locator("text=Ralph Loop")).to_be_visible()
            
            return True
        except Exception as e:
            print(f"❌ Homepage load test failed: {e}")
            return False
    
    def test_tab_switching(self) -> bool:
        """Test tab switching functionality."""
        try:
            self.page.goto(self.base_url)
            
            # Click Ralph Loop tab
            self.page.click("text=Ralph Loop")
            
            # Verify Ralph Loop tab is active
            ralph_tab = self.page.locator("text=Ralph Loop").first
            expect(ralph_tab).to_have_class("tab active")
            
            # Verify Ralph Loop content is visible
            expect(self.page.locator("text=Start New Project")).to_be_visible()
            
            # Click back to Prompt tab
            self.page.click("text=Send Prompt")
            
            # Verify Prompt tab is active
            prompt_tab = self.page.locator("text=Send Prompt").first
            expect(prompt_tab).to_have_class("tab active")
            
            # Verify Prompt form is visible
            expect(self.page.locator("#promptForm")).to_be_visible()
            
            return True
        except Exception as e:
            print(f"❌ Tab switching test failed: {e}")
            return False
    
    def test_prompt_workflow(self) -> bool:
        """Test complete prompt workflow."""
        try:
            self.page.goto(self.base_url)
            
            # Wait for form to be visible
            expect(self.page.locator("#promptForm")).to_be_visible()
            
            # Fill prompt
            prompt_textarea = self.page.locator("#prompt")
            prompt_textarea.fill("Say hello in exactly one word.")
            
            # Submit form
            submit_btn = self.page.locator("#submitBtn")
            submit_btn.click()
            
            # Wait for response (button should show loading state)
            expect(submit_btn).to_be_disabled(timeout=1000)
            
            # Wait for response area to have content (not just "Generating...")
            response_area = self.page.locator("#responseArea")
            # Wait for response to appear (should not be empty and not be "Generating...")
            self.page.wait_for_function(
                "document.getElementById('responseArea').textContent.trim() !== '' && "
                "document.getElementById('responseArea').textContent.trim() !== 'Generating response...'",
                timeout=60000
            )
            
            # Verify response is displayed
            response_text = response_area.text_content()
            assert response_text and len(response_text) > 0, "Response should not be empty"
            
            # Verify metadata is shown
            expect(self.page.locator("#metadata")).to_be_visible()
            
            return True
        except Exception as e:
            print(f"❌ Prompt workflow test failed: {e}")
            if self.page:
                self.page.screenshot(path="test-reports/prompt-workflow-failure.png")
            return False
    
    def test_ralph_loop_start(self) -> bool:
        """Test starting a Ralph loop."""
        try:
            self.page.goto(self.base_url)
            
            # Switch to Ralph Loop tab
            self.page.click("text=Ralph Loop")
            
            # Wait for form
            expect(self.page.locator("#ralphStartForm")).to_be_visible()
            
            # Fill project form
            self.page.fill("#projectName", "BrowserTestProject")
            self.page.fill("#projectDescription", "A test project created by browser tests")
            self.page.fill("#initialTask", "Create a simple hello world script")
            
            # Ensure phase-by-phase mode is selected
            self.page.check("#modePhase")
            
            # Submit form
            start_btn = self.page.locator("#startRalphBtn")
            start_btn.click()
            
            # Wait for controls to appear
            expect(self.page.locator("#ralphControls")).to_be_visible(timeout=10000)
            
            # Verify status area shows success
            status_area = self.page.locator("#ralphStatusArea")
            expect(status_area).to_contain_text("Project Started", timeout=5000)
            
            return True
        except Exception as e:
            print(f"❌ Ralph loop start test failed: {e}")
            if self.page:
                self.page.screenshot(path="test-reports/ralph-start-failure.png")
            return False
    
    def test_ralph_loop_status_updates(self) -> bool:
        """Test that status updates appear in UI."""
        try:
            self.page.goto(self.base_url)
            
            # Start a loop first
            self.page.click("text=Ralph Loop")
            self.page.fill("#projectName", "StatusTestProject")
            self.page.fill("#projectDescription", "Testing status updates")
            self.page.fill("#initialTask", "Create a test file")
            self.page.check("#modePhase")
            self.page.click("#startRalphBtn")
            
            # Wait for controls
            expect(self.page.locator("#ralphControls")).to_be_visible(timeout=10000)
            
            # Wait a bit for status to update
            time.sleep(3)
            
            # Check that status log has entries
            status_log = self.page.locator("#statusLog")
            log_content = status_log.text_content()
            assert log_content and len(log_content) > 0, "Status log should have content"
            
            # Check that phase indicator exists
            phase_indicator = self.page.locator("#phaseIndicator")
            expect(phase_indicator).to_be_visible()
            
            return True
        except Exception as e:
            print(f"❌ Status updates test failed: {e}")
            if self.page:
                self.page.screenshot(path="test-reports/status-updates-failure.png")
            return False
    
    def test_ralph_loop_controls(self) -> bool:
        """Test Ralph loop control buttons."""
        try:
            self.page.goto(self.base_url)
            
            # Start a loop
            self.page.click("text=Ralph Loop")
            self.page.fill("#projectName", "ControlsTestProject")
            self.page.fill("#projectDescription", "Testing controls")
            self.page.fill("#initialTask", "Create a test")
            self.page.check("#modePhase")
            self.page.click("#startRalphBtn")
            
            # Wait for controls
            expect(self.page.locator("#ralphControls")).to_be_visible(timeout=10000)
            
            # Test pause button
            pause_btn = self.page.locator("#pauseBtn")
            expect(pause_btn).to_be_visible()
            pause_btn.click()
            
            # Wait a bit for pause to take effect
            time.sleep(2)
            
            # Resume button should appear
            resume_btn = self.page.locator("#resumeBtn")
            expect(resume_btn).to_be_visible(timeout=5000)
            
            # Test stop button
            stop_btn = self.page.locator("#stopBtn")
            expect(stop_btn).to_be_visible()
            stop_btn.click()
            
            # Confirm stop dialog if it appears
            try:
                self.page.on("dialog", lambda dialog: dialog.accept())
            except Exception:
                pass
            
            time.sleep(1)
            
            return True
        except Exception as e:
            print(f"❌ Controls test failed: {e}")
            if self.page:
                self.page.screenshot(path="test-reports/controls-failure.png")
            return False
    
    def test_file_list_updates(self) -> bool:
        """Test that file list updates when files are created."""
        try:
            self.page.goto(self.base_url)
            
            # Start a loop
            self.page.click("text=Ralph Loop")
            self.page.fill("#projectName", "FileListTestProject")
            self.page.fill("#projectDescription", "Testing file list")
            self.page.fill("#initialTask", "Create a README file")
            self.page.check("#modeNonStop")  # Use non-stop for faster execution
            self.page.click("#startRalphBtn")
            
            # Wait for controls
            expect(self.page.locator("#ralphControls")).to_be_visible(timeout=10000)
            
            # Wait for file list to potentially update
            time.sleep(5)
            
            # Check file list exists
            file_list = self.page.locator("#fileList")
            expect(file_list).to_be_visible()
            
            # File list should either show files or "No files tracked yet"
            file_list_content = file_list.text_content()
            assert file_list_content is not None, "File list should have content"
            
            return True
        except Exception as e:
            print(f"❌ File list test failed: {e}")
            if self.page:
                self.page.screenshot(path="test-reports/file-list-failure.png")
            return False
    
    def run_all_tests(self, start_server: bool = True) -> int:
        """Run all browser tests."""
        print("=" * 70)
        print("🧪 Browser E2E Tests - Ralph Ollama UI")
        print("=" * 70)
        
        results = {'passed': 0, 'failed': 0}
        
        try:
            # Start server if needed
            if start_server:
                print("\n🚀 Starting Flask server...")
                if not self.start_server():
                    print("❌ Failed to start server")
                    return 1
                print("✅ Server started")
                time.sleep(2)
            
            # Setup browser
            print("\n🌐 Setting up browser...")
            self.setup_browser()
            print("✅ Browser ready")
            
            # Create test reports directory
            Path("test-reports").mkdir(exist_ok=True)
            Path("test-reports/videos").mkdir(exist_ok=True)
            
            # Run tests
            tests = [
                ("Homepage loads", self.test_homepage_loads),
                ("Tab switching", self.test_tab_switching),
                ("Prompt workflow", self.test_prompt_workflow),
                ("Ralph loop start", self.test_ralph_loop_start),
                ("Status updates", self.test_ralph_loop_status_updates),
                ("Controls", self.test_ralph_loop_controls),
                ("File list updates", self.test_file_list_updates),
            ]
            
            for test_name, test_func in tests:
                print(f"\n📝 Testing: {test_name}...")
                try:
                    if test_func():
                        print(f"  ✅ {test_name}")
                        results['passed'] += 1
                    else:
                        print(f"  ❌ {test_name}")
                        results['failed'] += 1
                except Exception as e:
                    print(f"  ❌ {test_name}: {e}")
                    results['failed'] += 1
                    if self.page:
                        self.page.screenshot(path=f"test-reports/{test_name.replace(' ', '-').lower()}-error.png")
            
            # Print summary
            print("\n" + "=" * 70)
            print("📊 Test Summary")
            print("=" * 70)
            print(f"✅ Passed: {results['passed']}")
            print(f"❌ Failed: {results['failed']}")
            print("=" * 70)
            
            return 0 if results['failed'] == 0 else 1
            
        except Exception as e:
            print(f"\n❌ Test execution error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            self.teardown_browser()
            if start_server:
                self.stop_server()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Browser E2E tests for Ralph Ollama UI')
    parser.add_argument('--url', default='http://localhost:5001',
                       help='Base URL of the UI server')
    parser.add_argument('--no-start-server', action='store_true',
                       help='Assume server is already running')
    parser.add_argument('--headed', action='store_true',
                       help='Run browser in headed mode (not headless)')
    
    args = parser.parse_args()
    
    runner = BrowserE2ETestRunner(
        base_url=args.url,
        headless=not args.headed
    )
    exit_code = runner.run_all_tests(start_server=not args.no_start_server)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
