"""
Ralph Ollama Integration Library
"""

from .ollama_client import OllamaClient, get_llm_response
from .exceptions import (
    OllamaError,
    OllamaServerError,
    OllamaConnectionError,
    OllamaModelError,
    OllamaConfigError,
    OllamaTimeoutError,
)
from .config import (
    get_config_path,
    get_workflow_config_path,
    get_default_model,
    is_ollama_enabled,
    load_and_validate_config,
    validate_ollama_config,
    validate_workflow_config,
    ConfigValidationError,
    ENV_PROVIDER,
    ENV_CONFIG,
    ENV_MODEL,
)
from .logging_config import setup_logging, setup_logging_from_config, get_logger

__all__ = [
    'OllamaClient',
    'get_llm_response',
    'get_config_path',
    'get_workflow_config_path',
    'get_default_model',
    'is_ollama_enabled',
    'load_and_validate_config',
    'validate_ollama_config',
    'validate_workflow_config',
    'ConfigValidationError',
    'OllamaError',
    'OllamaServerError',
    'OllamaConnectionError',
    'OllamaModelError',
    'OllamaConfigError',
    'OllamaTimeoutError',
    'setup_logging',
    'setup_logging_from_config',
    'get_logger',
    'ENV_PROVIDER',
    'ENV_CONFIG',
    'ENV_MODEL',
]
