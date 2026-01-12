#!/usr/bin/env python3
"""
Simple web UI for testing Ollama integration.
Shows connection status, allows sending prompts, and displays responses.
"""

import sys
import os
import json
import time
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
from lib.ralph_loop_engine import RalphLoopEngine, LoopMode, Phase

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)  # For session management

# Initialize clients
ollama_client: Optional[OllamaClient] = None
adapter: Optional[RalphOllamaAdapter] = None

# Ralph loop engines (keyed by session ID or project path)
ralph_loops: Dict[str, RalphLoopEngine] = {}

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


# Ralph Loop API Endpoints

@app.route('/api/ralph/start', methods=['POST'])
def ralph_start() -> Tuple[Response, int]:
    """Start a new Ralph loop for a project idea."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'success': False}), 400
        
        data = request.json or {}
        project_name = data.get('project_name', '')
        description = data.get('description', '')
        initial_task = data.get('initial_task', '')
        mode_str = data.get('mode', 'phase_by_phase')
        project_path = data.get('project_path', None)
        
        if not project_name:
            return jsonify({'error': 'Project name is required', 'success': False}), 400
        if not description:
            return jsonify({'error': 'Description is required', 'success': False}), 400
        
        # Determine project path
        if project_path:
            project_dir = Path(project_path)
        else:
            # Create in a projects directory
            projects_dir = project_root / 'projects'
            projects_dir.mkdir(exist_ok=True)
            # Sanitize project name for filesystem
            safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            project_dir = projects_dir / safe_name
        
        # Check if adapter is available
        if not adapter or not adapter.check_available():
            return jsonify({
                'error': 'Ollama adapter not available. Check server connection.',
                'success': False
            }), 503
        
        # Create or get loop engine
        session_id = str(project_dir)
        if session_id in ralph_loops:
            # Stop existing loop if running
            ralph_loops[session_id].stop()
        
        loop_engine = RalphLoopEngine(project_dir, adapter)
        ralph_loops[session_id] = loop_engine
        
        # Initialize project
        loop_engine.initialize_project(
            project_name=project_name,
            description=description,
            initial_task=initial_task if initial_task else None
        )
        
        # Determine mode
        mode = LoopMode.PHASE_BY_PHASE if mode_str == 'phase_by_phase' else LoopMode.NON_STOP
        
        # Start loop
        loop_engine.start(mode=mode)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'project_path': str(project_dir),
            'mode': mode.value
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to start loop: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/status', methods=['GET'])
def ralph_status() -> Tuple[Response, int]:
    """Get current loop status."""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id is required', 'success': False}), 400
        
        if session_id not in ralph_loops:
            return jsonify({
                'error': 'Loop not found',
                'success': False
            }), 404
        
        loop_engine = ralph_loops[session_id]
        status = loop_engine.get_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to get status: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/pause', methods=['POST'])
def ralph_pause() -> Tuple[Response, int]:
    """Pause execution."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'success': False}), 400
        
        data = request.json or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'session_id is required', 'success': False}), 400
        
        if session_id not in ralph_loops:
            return jsonify({
                'error': 'Loop not found',
                'success': False
            }), 404
        
        ralph_loops[session_id].pause()
        
        return jsonify({'success': True})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to pause: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/resume', methods=['POST'])
def ralph_resume() -> Tuple[Response, int]:
    """Resume execution with optional user input."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'success': False}), 400
        
        data = request.json or {}
        session_id = data.get('session_id')
        user_input = data.get('user_input', None)
        
        if not session_id:
            return jsonify({'error': 'session_id is required', 'success': False}), 400
        
        if session_id not in ralph_loops:
            return jsonify({
                'error': 'Loop not found',
                'success': False
            }), 404
        
        ralph_loops[session_id].resume(user_input=user_input)
        
        return jsonify({'success': True})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to resume: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/stop', methods=['POST'])
def ralph_stop() -> Tuple[Response, int]:
    """Stop execution."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'success': False}), 400
        
        data = request.json or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'session_id is required', 'success': False}), 400
        
        if session_id not in ralph_loops:
            return jsonify({
                'error': 'Loop not found',
                'success': False
            }), 404
        
        ralph_loops[session_id].stop()
        
        return jsonify({'success': True})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to stop: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/mode', methods=['POST'])
def ralph_mode() -> Tuple[Response, int]:
    """Switch between non-stop and phase-by-phase modes."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'success': False}), 400
        
        data = request.json or {}
        session_id = data.get('session_id')
        mode_str = data.get('mode')
        
        if not session_id:
            return jsonify({'error': 'session_id is required', 'success': False}), 400
        if not mode_str:
            return jsonify({'error': 'mode is required', 'success': False}), 400
        
        if session_id not in ralph_loops:
            return jsonify({
                'error': 'Loop not found',
                'success': False
            }), 404
        
        mode = LoopMode.PHASE_BY_PHASE if mode_str == 'phase_by_phase' else LoopMode.NON_STOP
        ralph_loops[session_id].set_mode(mode)
        
        return jsonify({
            'success': True,
            'mode': mode.value
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to change mode: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/files', methods=['GET'])
def ralph_files() -> Tuple[Response, int]:
    """Get list of files created/modified."""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id is required', 'success': False}), 400
        
        if session_id not in ralph_loops:
            return jsonify({
                'error': 'Loop not found',
                'success': False
            }), 404
        
        loop_engine = ralph_loops[session_id]
        files = loop_engine.file_tracker.get_all_files()
        changes = loop_engine.file_tracker.get_changes()
        
        return jsonify({
            'success': True,
            'files': files,
            'changes': changes
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to get files: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/stream', methods=['GET'])
def ralph_stream() -> Response:
    """Stream status updates using Server-Sent Events."""
    session_id = request.args.get('session_id')
    if not session_id or session_id not in ralph_loops:
        return Response("session_id not found", status=404, mimetype='text/plain')
    
    loop_engine = ralph_loops[session_id]
    
    def generate():
        last_log_count = 0
        while True:
            status = loop_engine.get_status()
            current_log_count = len(status.get('status_log', []))
            
            # Send new log entries
            if current_log_count > last_log_count:
                new_entries = status['status_log'][last_log_count:]
                for entry in new_entries:
                    yield f"data: {json.dumps(entry)}\n\n"
                last_log_count = current_log_count
            
            # Send periodic status update
            yield f"data: {json.dumps({'type': 'status', 'data': status})}\n\n"
            
            time.sleep(1)  # Poll every second
    
    return Response(generate(), mimetype='text/event-stream')


def main():
    """Main entry point for UI server."""
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


if __name__ == '__main__':
    main()
