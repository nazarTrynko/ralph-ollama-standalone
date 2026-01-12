#!/usr/bin/env python3
"""
Simple web UI for testing Ollama integration.
Shows connection status, allows sending prompts, and displays responses.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS

# Add project root to path to enable package imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import from packages
from lib.ollama_client import OllamaClient
from lib.exceptions import (
    OllamaError,
    OllamaConnectionError,
    OllamaModelError,
    OllamaConfigError,
    OllamaServerError,
    OllamaTimeoutError,
)
from integration.ralph_ollama_adapter import RalphOllamaAdapter, call_llm

app = Flask(__name__)
CORS(app)

# Initialize clients
ollama_client: Optional[OllamaClient] = None
adapter: Optional[RalphOllamaAdapter] = None

def init_clients() -> None:
    """Initialize Ollama clients."""
    global ollama_client, adapter
    try:
        ollama_client = OllamaClient()
        adapter = RalphOllamaAdapter()
        print(f"✅ Clients initialized successfully")
        print(f"   Server: {ollama_client.base_url}")
        print(f"   Default model: {ollama_client.default_model}")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize clients: {e}")
        print(f"   This is OK if Ollama isn't running yet")
        ollama_client = None
        adapter = None

init_clients()


@app.route('/')
def index() -> str:
    """Serve the main UI page."""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def get_status() -> Tuple[Response, int]:
    """Get Ollama server status and available models."""
    try:
        if not ollama_client:
            return jsonify({
                'connected': False,
                'error': 'Client not initialized',
                'server_url': None,
                'default_model': None,
                'models': [],
                'adapter_available': False
            }), 200  # Return 200 so UI can display the error
        
        connected = ollama_client.check_server()
        models = []
        default_model = ollama_client.default_model
        
        if connected:
            try:
                models = ollama_client.list_models()
            except OllamaConnectionError as e:
                print(f"Warning: Connection error listing models: {e}")
                models = []
            except OllamaServerError as e:
                print(f"Warning: Server error listing models: {e}")
                models = []
            except Exception as e:
                print(f"Warning: Could not list models: {e}")
                models = []
        
        return jsonify({
            'connected': connected,
            'server_url': ollama_client.base_url if ollama_client else None,
            'default_model': default_model,
            'models': models,
            'adapter_available': adapter.check_available() if adapter else False
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'connected': False,
            'error': str(e),
            'server_url': None,
            'default_model': None,
            'models': [],
            'adapter_available': False
        }), 200  # Return 200 so UI can display the error


@app.route('/api/generate', methods=['POST'])
def generate() -> Tuple[Response, int]:
    """Generate a response from Ollama."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'success': False}), 400
        
        data = request.json or {}
        prompt = data.get('prompt', '')
        model = data.get('model', None)
        task_type = data.get('task_type', None)
        system_prompt = data.get('system_prompt', None)
        
        if not prompt:
            return jsonify({'error': 'Prompt is required', 'success': False}), 400
        
        if not ollama_client:
            return jsonify({
                'error': 'Ollama client not initialized. Check server logs.',
                'success': False
            }), 500
        
        # Check server first
        if not ollama_client.check_server():
            return jsonify({
                'error': 'Ollama server is not running. Start it with: ollama serve',
                'success': False
            }), 503
        
        # Use adapter if available, otherwise use client directly
        if adapter and adapter.check_available():
            result = adapter.generate(
                prompt=prompt,
                model=model,
                task_type=task_type,
                system_prompt=system_prompt
            )
            return jsonify({
                'response': result.get('content', ''),
                'model': result.get('model', ''),
                'provider': result.get('provider', 'ollama'),
                'tokens': result.get('tokens', {}),
                'success': True
            })
        else:
            # Fallback to direct client
            result = ollama_client.generate(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt
            )
            return jsonify({
                'response': result.get('response', ''),
                'model': result.get('model', ''),
                'provider': 'ollama',
                'tokens': result.get('tokens', {}),
                'success': True
            })
    except OllamaConnectionError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'connection',
            'success': False
        }), 503
    except OllamaModelError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'model',
            'model': e.model if hasattr(e, 'model') else None,
            'available_models': e.available_models if hasattr(e, 'available_models') else None,
            'success': False
        }), 400
    except OllamaConfigError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'config',
            'success': False
        }), 500
    except OllamaTimeoutError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'timeout',
            'success': False
        }), 504
    except OllamaServerError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'server',
            'status_code': e.status_code if hasattr(e, 'status_code') else None,
            'success': False
        }), 502
    except OllamaError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'ollama',
            'success': False
        }), 500
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()  # Print to server console
        return jsonify({
            'error': f'Unexpected error: {error_msg}',
            'error_type': 'unknown',
            'success': False
        }), 500


@app.route('/api/models', methods=['GET'])
def list_models() -> Tuple[Response, int]:
    """List available models."""
    if not ollama_client:
        return jsonify({'error': 'Client not initialized'}), 500
    
    try:
        if not ollama_client.check_server():
            return jsonify({
                'error': 'Ollama server is not running'
            }), 503
        
        models = ollama_client.list_models()
        return jsonify({
            'models': models,
            'default': ollama_client.default_model
        })
    except OllamaConnectionError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'connection'
        }), 503
    except OllamaServerError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'server',
            'status_code': e.status_code if hasattr(e, 'status_code') else None
        }), 502
    except OllamaError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'ollama'
        }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'error_type': 'unknown'
        }), 500


if __name__ == '__main__':
    # Use port from environment or default to 5001 (5000 is often used by AirPlay on macOS)
    port = int(os.getenv('FLASK_PORT', 5001))
    
    print("=" * 60)
    print("Ralph Ollama UI Server")
    print("=" * 60)
    print(f"\nStarting server on http://localhost:{port}")
    print(f"Open your browser to http://localhost:{port}")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=port)
