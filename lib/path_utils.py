#!/usr/bin/env python3
"""
Path utilities for Ralph Ollama integration.
Provides centralized path management and project root detection.
"""

import sys
from pathlib import Path
from typing import Optional

_PROJECT_ROOT: Optional[Path] = None


def get_project_root() -> Path:
    """Get project root directory.
    
    Finds the project root by looking for pyproject.toml file.
    Falls back to lib parent directory if not found.
    
    Returns:
        Path to project root directory
    """
    global _PROJECT_ROOT
    
    if _PROJECT_ROOT is None:
        # Try to find project root by looking for pyproject.toml
        current = Path(__file__).parent
        while current != current.parent:
            if (current / 'pyproject.toml').exists():
                _PROJECT_ROOT = current
                break
            current = current.parent
        else:
            # Fallback to lib parent
            _PROJECT_ROOT = Path(__file__).parent.parent
    
    return _PROJECT_ROOT


def setup_paths() -> None:
    """Add project root to sys.path if not already present.
    
    This enables imports from lib/ and integration/ directories
    without requiring package installation.
    """
    project_root = get_project_root()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def get_config_path() -> Path:
    """Get config directory path.
    
    Returns:
        Path to config directory
    """
    return get_project_root() / 'config'


def get_cache_path() -> Path:
    """Get cache directory path.
    
    Returns:
        Path to cache directory (state/cache)
    """
    return get_project_root() / 'state' / 'cache'


def get_state_path() -> Path:
    """Get state directory path.
    
    Returns:
        Path to state directory
    """
    return get_project_root() / 'state'
