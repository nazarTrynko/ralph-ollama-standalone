#!/usr/bin/env python3
"""
Quick test script for the UI endpoints.
Tests the Flask app without starting the web server.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ui.app import app, ollama_client, adapter

def test_status_endpoint():
    """Test the /api/status endpoint."""
    print("Testing /api/status endpoint...")
    with app.test_client() as client:
        response = client.get('/api/status')
        print(f"  Status code: {response.status_code}")
        data = response.get_json()
        print(f"  Response: {data}")
        if response.status_code == 200:
            print("  ✅ Status endpoint works")
        else:
            print("  ❌ Status endpoint failed")
        return response.status_code == 200

def test_generate_endpoint():
    """Test the /api/generate endpoint."""
    print("\nTesting /api/generate endpoint...")
    with app.test_client() as client:
        test_data = {
            'prompt': 'Say hello in one word.',
            'model': None,
            'task_type': None
        }
        response = client.post('/api/generate', 
                              json=test_data,
                              content_type='application/json')
        print(f"  Status code: {response.status_code}")
        data = response.get_json()
        if response.status_code == 200:
            print(f"  ✅ Generate endpoint works")
            print(f"  Response preview: {data.get('response', '')[:50]}...")
        elif response.status_code == 503:
            print(f"  ⚠️  Ollama server not running: {data.get('error', 'Unknown error')}")
        else:
            print(f"  ❌ Generate endpoint failed: {data.get('error', 'Unknown error')}")
        return response.status_code in [200, 503]  # 503 is OK if Ollama isn't running

def test_client_initialization():
    """Test client initialization."""
    print("\nTesting client initialization...")
    if ollama_client:
        print(f"  ✅ Ollama client initialized")
        print(f"  Server URL: {ollama_client.base_url}")
        print(f"  Default model: {ollama_client.default_model}")
        try:
            connected = ollama_client.check_server()
            print(f"  Server connected: {connected}")
        except Exception as e:
            print(f"  ⚠️  Error checking server: {e}")
    else:
        print("  ❌ Ollama client not initialized")
        return False
    return True

def main():
    print("=" * 60)
    print("UI Test Suite")
    print("=" * 60)
    
    # Test client initialization
    client_ok = test_client_initialization()
    
    # Test status endpoint
    status_ok = test_status_endpoint()
    
    # Test generate endpoint
    generate_ok = test_generate_endpoint()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Client initialization: {'✅' if client_ok else '❌'}")
    print(f"Status endpoint: {'✅' if status_ok else '❌'}")
    print(f"Generate endpoint: {'✅' if generate_ok else '⚠️  (Ollama may not be running)'}")
    print("=" * 60)
    
    if client_ok and status_ok:
        print("\n✅ UI is ready! Start the server with: python3 ui/app.py")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
