"""
Ralph Ollama Integration Library
"""

from .ollama_client import OllamaClient, get_llm_response
from .config import (
    get_config_path,
    get_workflow_config_path,
    get_default_model,
    is_ollama_enabled,
    ENV_PROVIDER,
    ENV_CONFIG,
    ENV_MODEL,
)

__all__ = [
    'OllamaClient',
    'get_llm_response',
    'get_config_path',
    'get_workflow_config_path',
    'get_default_model',
    'is_ollama_enabled',
    'ENV_PROVIDER',
    'ENV_CONFIG',
    'ENV_MODEL',
]
