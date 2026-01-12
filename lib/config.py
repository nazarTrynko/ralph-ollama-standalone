"""
Configuration constants and utilities for Ralph Ollama integration.
"""

import os
import json
import warnings
from pathlib import Path
from typing import Optional, Dict, Any, List

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


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def validate_ollama_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate Ollama configuration structure and types.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        List of validation warnings (empty if valid)
        
    Raises:
        ConfigValidationError: If configuration is invalid
    """
    warnings_list = []
    
    # Required top-level keys
    required_keys = ['server', 'defaultModel']
    for key in required_keys:
        if key not in config:
            raise ConfigValidationError(f"Missing required key: {key}")
    
    # Validate server section
    server = config.get('server', {})
    if not isinstance(server, dict):
        raise ConfigValidationError("'server' must be a dictionary")
    
    required_server_keys = ['baseUrl']
    for key in required_server_keys:
        if key not in server:
            raise ConfigValidationError(f"Missing required server key: {key}")
    
    # Validate server values
    if 'port' in server:
        port = server['port']
        if not isinstance(port, int) or port < 1 or port > 65535:
            warnings_list.append(f"Invalid server port: {port} (should be 1-65535)")
    
    if 'timeout' in server:
        timeout = server['timeout']
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            warnings_list.append(f"Invalid server timeout: {timeout} (should be > 0)")
    
    # Validate defaultModel
    default_model = config.get('defaultModel')
    if not isinstance(default_model, str) or not default_model:
        raise ConfigValidationError("'defaultModel' must be a non-empty string")
    
    # Validate models section (optional but if present, should be dict)
    models = config.get('models', {})
    if models and not isinstance(models, dict):
        raise ConfigValidationError("'models' must be a dictionary")
    
    # Validate each model configuration
    for model_name, model_config in models.items():
        if not isinstance(model_config, dict):
            warnings_list.append(f"Model '{model_name}' configuration must be a dictionary")
            continue
        
        # Validate model parameters
        params = model_config.get('parameters', {})
        if params:
            if not isinstance(params, dict):
                warnings_list.append(f"Model '{model_name}' parameters must be a dictionary")
            else:
                # Validate parameter types and ranges
                if 'temperature' in params:
                    temp = params['temperature']
                    if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                        warnings_list.append(f"Model '{model_name}' temperature should be 0-2, got {temp}")
                
                if 'topP' in params:
                    top_p = params['topP']
                    if not isinstance(top_p, (int, float)) or top_p < 0 or top_p > 1:
                        warnings_list.append(f"Model '{model_name}' topP should be 0-1, got {top_p}")
    
    # Validate retry section (optional)
    retry = config.get('retry', {})
    if retry:
        if not isinstance(retry, dict):
            warnings_list.append("'retry' must be a dictionary")
        else:
            if 'maxAttempts' in retry:
                max_attempts = retry['maxAttempts']
                if not isinstance(max_attempts, int) or max_attempts < 1:
                    warnings_list.append(f"Invalid maxAttempts: {max_attempts} (should be >= 1)")
    
    return warnings_list


def validate_workflow_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate workflow configuration structure and types.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        List of validation warnings (empty if valid)
        
    Raises:
        ConfigValidationError: If configuration is invalid
    """
    warnings_list = []
    
    # Validate workflow section (optional but if present, should be dict)
    workflow = config.get('workflow', {})
    if workflow and not isinstance(workflow, dict):
        warnings_list.append("'workflow' must be a dictionary")
    elif workflow:
        # Validate tasks
        tasks = workflow.get('tasks', {})
        if tasks and not isinstance(tasks, dict):
            warnings_list.append("'workflow.tasks' must be a dictionary")
        else:
            for task_name, task_config in tasks.items():
                if not isinstance(task_config, dict):
                    warnings_list.append(f"Task '{task_name}' configuration must be a dictionary")
                    continue
                
                # Validate preferredModel and fallbackModel
                if 'preferredModel' in task_config:
                    model = task_config['preferredModel']
                    if not isinstance(model, str) or not model:
                        warnings_list.append(f"Task '{task_name}' preferredModel must be a non-empty string")
    
    # Validate performance section (optional)
    performance = config.get('performance', {})
    if performance and not isinstance(performance, dict):
        warnings_list.append("'performance' must be a dictionary")
    elif performance:
        if 'timeoutSeconds' in performance:
            timeout = performance['timeoutSeconds']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                warnings_list.append(f"Invalid timeoutSeconds: {timeout} (should be > 0)")
    
    return warnings_list


def load_and_validate_config(config_path: Path, use_pydantic: bool = True) -> Dict[str, Any]:
    """
    Load and validate configuration file.
    
    Args:
        config_path: Path to configuration file
        use_pydantic: Whether to use Pydantic validation (default: True)
    
    Returns:
        Validated configuration dictionary
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config is not valid JSON
        ConfigValidationError: If config validation fails
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigValidationError(f"Invalid JSON in config file {config_path}: {e}")
    
    # Try Pydantic validation first if enabled
    if use_pydantic:
        try:
            from lib.config_models import (
                validate_ollama_config_pydantic,
                validate_workflow_config_pydantic
            )
            
            # Determine which validation function to use
            if 'server' in config or 'defaultModel' in config:
                # Ollama config
                validated_model = validate_ollama_config_pydantic(config)
                # Convert back to dict for backward compatibility
                return validated_model.dict()
            else:
                # Workflow config
                validated_model = validate_workflow_config_pydantic(config)
                # Convert back to dict for backward compatibility
                return validated_model.dict()
        except ImportError:
            # Pydantic not available, fall back to manual validation
            warnings.warn("Pydantic not available, using manual validation", UserWarning)
            use_pydantic = False
        except ValueError as e:
            # Pydantic validation failed, fall back to manual validation with warning
            warnings.warn(f"Pydantic validation failed: {e}, falling back to manual validation", UserWarning)
            use_pydantic = False
    
    # Fall back to manual validation
    if not use_pydantic:
        # Determine which validation function to use
        if 'server' in config or 'defaultModel' in config:
            warnings_list = validate_ollama_config(config)
        else:
            warnings_list = validate_workflow_config(config)
        
        # Emit warnings but don't fail
        for warning in warnings_list:
            warnings.warn(f"Config validation warning: {warning}", UserWarning)
    
    return config
