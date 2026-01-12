"""
Browser test fixtures and setup for Playwright-based e2e tests.
"""

import pytest
import subprocess
import sys
import time
import signal
from pathlib import Path
from typing import Optional, Generator

from lib.path_utils import setup_paths
setup_paths()


@pytest.fixture(scope="session")
def flask_server() -> Generator[Optional[subprocess.Popen], None, None]:
    """Start Flask server for browser tests."""
    server_process = None
    try:
        # Start Flask server
        server_process = subprocess.Popen(
            [sys.executable, str(project_root / 'ui' / 'app.py')],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root)
        )
        
        # Wait for server to start
        max_attempts = 30
        for i in range(max_attempts):
            try:
                import requests
                response = requests.get("http://localhost:5001/", timeout=2)
                if response.status_code == 200:
                    break
            except Exception:
                if i == max_attempts - 1:
                    pytest.fail("Flask server did not start in time")
                time.sleep(1)
        
        yield server_process
        
    finally:
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            except Exception:
                pass


@pytest.fixture(scope="function")
def base_url(flask_server) -> str:
    """Base URL for the Flask app."""
    return "http://localhost:5001"
