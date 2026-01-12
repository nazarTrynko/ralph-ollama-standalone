"""
Configuration constants and utilities for Ralph Ollama integration.
"""

import os
from pathlib import Path
from typing import Optional

# Default configuration paths (relative to project root)
DEFAULT_CONFIG_PATH = 'config/ollama-config.json'
DEFAULT_WORKFLOW_CONFIG_PATH = 'config/workflow-config.json'

# Environment variable names
ENV_PROVIDER = 'RALPH_LLM_PROVIDER'
ENV_CONFIG = 'RALPH_OLLAMA_CONFIG'
ENV_MODEL = 'RALPH_LLM_MODEL'
ENV_WORKFLOW_CONFIG = 'RALPH_WORKFLOW_CONFIG'


def get_config_path() -> Path:
    """Get Ollama config path from env or default."""
    config_path = os.getenv(ENV_CONFIG, DEFAULT_CONFIG_PATH)
    return Path(config_path)


def get_workflow_config_path() -> Path:
    """Get workflow config path from env or default."""
    config_path = os.getenv(ENV_WORKFLOW_CONFIG, DEFAULT_WORKFLOW_CONFIG_PATH)
    return Path(config_path)


def get_default_model() -> str:
    """Get default model from env or default."""
    return os.getenv(ENV_MODEL, 'llama3.2')


def is_ollama_enabled() -> bool:
    """Check if Ollama is enabled via environment."""
    return os.getenv(ENV_PROVIDER, '').lower() == 'ollama'
