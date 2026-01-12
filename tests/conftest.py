"""
Pytest configuration and fixtures for Ralph Ollama tests.
"""

import pytest
from pathlib import Path
from typing import Optional
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def config_path() -> Path:
    """Return path to test config file."""
    return Path(__file__).parent.parent / 'config' / 'ollama-config.json'


@pytest.fixture
def workflow_config_path() -> Path:
    """Return path to workflow config file."""
    return Path(__file__).parent.parent / 'config' / 'workflow-config.json'


@pytest.fixture
def mock_ollama_server(monkeypatch):
    """Mock Ollama server responses."""
    import requests
    
    class MockResponse:
        def __init__(self, json_data: dict, status_code: int = 200):
            self.json_data = json_data
            self.status_code = status_code
        
        def json(self):
            return self.json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")
    
    def mock_get(url: str, **kwargs):
        if '/api/tags' in url:
            return MockResponse({
                'models': [
                    {'name': 'llama3.2'},
                    {'name': 'codellama'},
                ]
            })
        return MockResponse({})
    
    def mock_post(url: str, **kwargs):
        if '/api/generate' in url:
            return MockResponse({
                'response': 'Hello, world!',
                'model': 'llama3.2',
                'prompt_eval_count': 10,
                'eval_count': 5,
                'done': True
            })
        return MockResponse({})
    
    monkeypatch.setattr(requests, 'get', mock_get)
    monkeypatch.setattr(requests, 'post', mock_post)
    
    return mock_get, mock_post
