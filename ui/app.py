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
from datetime import datetime
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
from lib.response_cache import get_cache

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
        
        # Check cache for model list
        cache = get_cache()
        cached_models = cache.get('model_list', 'all')
        
        if cached_models:
            models = cached_models
        else:
            models = ollama_client.list_models()
            # Cache model list (shorter TTL for model lists)
            cache.set('model_list', 'all', models)
        
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
        model = data.get('model', None)  # Get model from request
        
        # Determine project path
        is_existing_project = False
        if project_path:
            project_dir = Path(project_path)
            # Check if project exists
            if project_dir.exists() and (project_dir / '@fix_plan.md').exists():
                # Loading existing project - skip initialization
                is_existing_project = True
            else:
                return jsonify({
                    'error': f'Project not found at {project_path}',
                    'success': False
                }), 404
        else:
            # Creating new project
            if not project_name:
                return jsonify({'error': 'Project name is required', 'success': False}), 400
            if not description:
                return jsonify({'error': 'Description is required', 'success': False}), 400
            
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
        
        loop_engine = RalphLoopEngine(project_dir, adapter, model=model)
        ralph_loops[session_id] = loop_engine
        
        # Initialize project only if it's new
        if not is_existing_project:
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


@app.route('/api/ralph/projects', methods=['GET'])
def list_projects() -> Tuple[Response, int]:
    """List all existing projects."""
    try:
        projects_dir = project_root / 'projects'
        projects = []
        
        if projects_dir.exists():
            for project_dir in sorted(projects_dir.iterdir()):
                if not project_dir.is_dir():
                    continue
                
                # Skip test projects
                project_name = project_dir.name
                if project_name.startswith('Test') or 'Test' in project_name:
                    continue
                
                # Read project metadata
                readme_path = project_dir / 'README.md'
                fix_plan_path = project_dir / '@fix_plan.md'
                
                name = project_name
                description = ''
                has_fix_plan = fix_plan_path.exists()
                last_modified = None
                
                if readme_path.exists():
                    try:
                        content = readme_path.read_text()
                        lines = content.split('\n')
                        # Extract name from first line (header)
                        for line in lines:
                            if line.startswith('# '):
                                name = line[2:].strip()
                                break
                        # Extract description (first paragraph after title)
                        desc_lines = []
                        in_desc = False
                        for line in lines:
                            if line.startswith('# '):
                                in_desc = True
                                continue
                            if in_desc and line.strip() and not line.startswith('#'):
                                desc_lines.append(line.strip())
                            elif in_desc and line.startswith('#'):
                                break
                        if desc_lines:
                            description = ' '.join(desc_lines[:2])  # First 2 lines
                    except Exception as e:
                        print(f"Error reading README for {project_dir}: {e}")
                
                # Get last modified time
                if fix_plan_path.exists():
                    last_modified = datetime.fromtimestamp(fix_plan_path.stat().st_mtime).isoformat()
                elif readme_path.exists():
                    last_modified = datetime.fromtimestamp(readme_path.stat().st_mtime).isoformat()
                else:
                    last_modified = datetime.fromtimestamp(project_dir.stat().st_mtime).isoformat()
                
                projects.append({
                    'name': name,
                    'path': str(project_dir),
                    'description': description,
                    'last_modified': last_modified,
                    'has_fix_plan': has_fix_plan
                })
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to list projects: {str(e)}',
            'success': False,
            'projects': []
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


@app.route('/api/ralph/file/content', methods=['GET'])
def ralph_file_content() -> Tuple[Response, int]:
    """Get content of a specific file."""
    try:
        session_id = request.args.get('session_id')
        file_path = request.args.get('file_path')
        
        if not session_id:
            return jsonify({'error': 'session_id is required', 'success': False}), 400
        if not file_path:
            return jsonify({'error': 'file_path is required', 'success': False}), 400
        
        if session_id not in ralph_loops:
            return jsonify({
                'error': 'Loop not found',
                'success': False
            }), 404
        
        loop_engine = ralph_loops[session_id]
        full_path = loop_engine.project_path / file_path
        
        # Security check: ensure file is within project directory
        try:
            full_path.resolve().relative_to(loop_engine.project_path.resolve())
        except ValueError:
            return jsonify({
                'error': 'Invalid file path',
                'success': False
            }), 400
        
        if not full_path.exists():
            return jsonify({
                'error': 'File not found',
                'success': False
            }), 404
        
        if not full_path.is_file():
            return jsonify({
                'error': 'Path is not a file',
                'success': False
            }), 400
        
        # Read file content
        try:
            content = full_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try binary mode for non-text files
            return jsonify({
                'error': 'File is not a text file',
                'success': False
            }), 400
        
        return jsonify({
            'success': True,
            'content': content,
            'path': file_path,
            'size': full_path.stat().st_size
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to read file: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/file/save', methods=['POST'])
def ralph_file_save() -> Tuple[Response, int]:
    """Save content to a file."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'success': False}), 400
        
        data = request.json or {}
        session_id = data.get('session_id')
        file_path = data.get('file_path')
        content = data.get('content')
        
        if not session_id:
            return jsonify({'error': 'session_id is required', 'success': False}), 400
        if not file_path:
            return jsonify({'error': 'file_path is required', 'success': False}), 400
        if content is None:
            return jsonify({'error': 'content is required', 'success': False}), 400
        
        if session_id not in ralph_loops:
            return jsonify({
                'error': 'Loop not found',
                'success': False
            }), 404
        
        loop_engine = ralph_loops[session_id]
        full_path = loop_engine.project_path / file_path
        
        # Security check: ensure file is within project directory
        try:
            full_path.resolve().relative_to(loop_engine.project_path.resolve())
        except ValueError:
            return jsonify({
                'error': 'Invalid file path',
                'success': False
            }), 400
        
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file content
        full_path.write_text(content, encoding='utf-8')
        
        # Invalidate file list cache
        cache = get_cache()
        cache.invalidate('file_list', {'session_id': session_id})
        
        return jsonify({
            'success': True,
            'path': file_path,
            'size': full_path.stat().st_size
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to save file: {str(e)}',
            'success': False
        }), 500


@app.route('/api/ralph/stream', methods=['GET'])
def ralph_stream() -> Response:
    """Stream status updates using Server-Sent Events with smart change detection."""
    session_id = request.args.get('session_id')
    if not session_id or session_id not in ralph_loops:
        return Response("session_id not found", status=404, mimetype='text/plain')
    
    loop_engine = ralph_loops[session_id]
    
    def generate():
        last_status_hash = None
        last_log_count = 0
        consecutive_no_change = 0
        poll_interval = 0.5  # Start with 500ms
        
        while True:
            try:
                status = loop_engine.get_status()
                
                # Create a hash of key status fields to detect changes
                status_key = {
                    'phase': status.get('current_phase'),
                    'is_running': status.get('is_running'),
                    'is_paused': status.get('is_paused'),
                    'task': status.get('current_task'),
                    'progress': status.get('progress', {}).get('task_progress', 0),
                    'files_created': status.get('progress', {}).get('files_created', 0)
                }
                status_hash = hash(json.dumps(status_key, sort_keys=True))
                
                # Check for new log entries
                current_log_count = len(status.get('status_log', []))
                has_new_logs = current_log_count > last_log_count
                
                # Check if status actually changed
                status_changed = status_hash != last_status_hash
                
                if status_changed or has_new_logs:
                    # Send new log entries
                    if has_new_logs:
                        new_entries = status['status_log'][last_log_count:]
                        for entry in new_entries:
                            yield f"data: {json.dumps({'type': 'log', 'data': entry})}\n\n"
                        last_log_count = current_log_count
                    
                    # Send status update only if changed
                    if status_changed:
                        yield f"data: {json.dumps({'type': 'status', 'data': status})}\n\n"
                        last_status_hash = status_hash
                        consecutive_no_change = 0
                        poll_interval = 0.5  # Reset to fast polling when active
                    else:
                        consecutive_no_change += 1
                else:
                    consecutive_no_change += 1
                
                # Adaptive polling: slow down when no changes
                if consecutive_no_change > 10:
                    poll_interval = min(2.0, poll_interval * 1.1)  # Gradually increase up to 2s
                elif consecutive_no_change > 5:
                    poll_interval = 1.0  # Medium speed
                
                # Send heartbeat every 10 seconds to keep connection alive
                if consecutive_no_change % 20 == 0:
                    yield f": heartbeat\n\n"
                
                time.sleep(poll_interval)
                
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                time.sleep(1)
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # Disable buffering in nginx
    return response


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
