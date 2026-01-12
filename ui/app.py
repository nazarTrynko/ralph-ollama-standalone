#!/usr/bin/env python3
"""
Simple web UI for testing Ollama integration.
Shows connection status, allows sending prompts, and displays responses.
"""

import sys
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Add project root to path to enable package imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import from packages
from lib.ollama_client import OllamaClient
from integration.ralph_ollama_adapter import RalphOllamaAdapter, call_llm

app = Flask(__name__)
CORS(app)

# Initialize clients
ollama_client = None
adapter = None

def init_clients():
    """Initialize Ollama clients."""
    global ollama_client, adapter
    try:
        ollama_client = OllamaClient()
        adapter = RalphOllamaAdapter()
    except Exception as e:
        print(f"Warning: Could not initialize clients: {e}")
        ollama_client = None
        adapter = None

init_clients()


@app.route('/')
def index():
    """Serve the main UI page."""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get Ollama server status and available models."""
    if not ollama_client:
        return jsonify({
            'connected': False,
            'error': 'Client not initialized'
        }), 500
    
    try:
        connected = ollama_client.check_server()
        models = []
        default_model = ollama_client.default_model
        
        if connected:
            try:
                models = ollama_client.list_models()
            except Exception as e:
                models = []
        
        return jsonify({
            'connected': connected,
            'server_url': ollama_client.base_url if ollama_client else None,
            'default_model': default_model,
            'models': models,
            'adapter_available': adapter.check_available() if adapter else False
        })
    except Exception as e:
        return jsonify({
            'connected': False,
            'error': str(e)
        }), 500


@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate a response from Ollama."""
    data = request.json
    prompt = data.get('prompt', '')
    model = data.get('model', None)
    task_type = data.get('task_type', None)
    system_prompt = data.get('system_prompt', None)
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    if not ollama_client:
        return jsonify({'error': 'Ollama client not initialized'}), 500
    
    try:
        # Check server first
        if not ollama_client.check_server():
            return jsonify({
                'error': 'Ollama server is not running. Start it with: ollama serve'
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
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/api/models', methods=['GET'])
def list_models():
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
