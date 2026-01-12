#!/usr/bin/env python3
"""
Ralph Ollama Adapter
Provides a drop-in adapter for Ralph workflow to use Ollama instead of cloud APIs.

This adapter can be used to replace cloud LLM calls in Ralph workflow implementations.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from lib.path_utils import setup_paths
setup_paths()

from lib.ollama_client import OllamaClient
from lib.config import (
    is_ollama_enabled,
    get_config_path,
    get_workflow_config_path,
    load_and_validate_config,
    DEFAULT_CONFIG_PATH,
)
from lib.exceptions import (
    OllamaError,
    OllamaConnectionError,
    OllamaModelError,
    OllamaConfigError,
)
from lib.logging_config import get_logger
from lib.response_cache import get_cache

logger = get_logger('adapter')


class RalphOllamaAdapter:
    """
    Adapter that makes OllamaClient compatible with Ralph workflow patterns.
    
    This adapter provides a standardized interface that can be used as a drop-in
    replacement for cloud-based LLM providers in Ralph workflow implementations.
    """
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize adapter with Ollama configuration."""
        logger.debug(f"Initializing RalphOllamaAdapter with config: {config_path}")
        self.client: OllamaClient = OllamaClient(config_path)
        self.config_path: Optional[str] = config_path
        logger.info("RalphOllamaAdapter initialized")
        
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        task_type: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generate response from Ollama.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model name (if None, auto-selects based on task_type)
            task_type: Task type for automatic model selection (implementation, testing, etc.)
            **kwargs: Additional parameters (temperature, etc.)
        
        Returns:
            Dictionary with 'content', 'model', 'tokens', 'provider' keys
        """
        # Auto-select model based on task type if model not specified
        if model is None and task_type:
            model = self._select_model_for_task(task_type)
            logger.debug(f"Auto-selected model '{model}' for task type '{task_type}'")
        
        logger.info(f"Generating response: task_type={task_type}, model={model}")
        
        # Check cache
        cache = get_cache()
        cache_key = {
            'prompt': prompt,
            'system_prompt': system_prompt,
            'model': model,
            'kwargs': kwargs
        }
        cached_response = cache.get('llm_response', cache_key)
        
        if cached_response:
            logger.debug("Using cached LLM response")
            return cached_response
        
        # Generate response
        result = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            **kwargs
        )
        
        # Format response to match Ralph workflow expectations
        response = {
            'content': result['response'],
            'model': result['model'],
            'provider': 'ollama',
            'tokens': result.get('tokens', {}),
            'done': result.get('done', True)
        }
        
        # Cache response
        cache.set('llm_response', cache_key, response)
        
        return response
    
    def _select_model_for_task(self, task_type: str) -> str:
        """Select appropriate model for task type."""
        # Load workflow config to get task-based model selection
        preferred_model = None
        fallback_model = None
        try:
            workflow_config_path = get_workflow_config_path()
            if workflow_config_path.exists():
                config = load_and_validate_config(workflow_config_path)
                
                tasks = config.get('workflow', {}).get('tasks', {})
                task_config = tasks.get(task_type, {})
                preferred_model = task_config.get('preferredModel')
                fallback_model = task_config.get('fallbackModel')
        except Exception as e:
            logger.debug(f"Could not load workflow config: {e}")
            pass
        
        # Fallback: simple mapping
        if preferred_model is None:
            model_map = {
                'implementation': 'codellama',
                'code-review': 'codellama',
                'refactoring': 'codellama',
                'testing': 'llama3.2',
                'documentation': 'llama3.2',
            }
            preferred_model = model_map.get(task_type)
        
        # Use fallback if not set
        if fallback_model is None:
            fallback_model = 'llama3.2'
        
        # Try to verify model availability and use fallback if needed
        selected_model = preferred_model or self.client.default_model
        if self._is_model_available(selected_model):
            return selected_model
        
        # Preferred model not available, try fallback
        if fallback_model and self._is_model_available(fallback_model):
            logger.warning(f"Preferred model '{preferred_model}' not available, using fallback '{fallback_model}'")
            return fallback_model
        
        # Fallback not available, use default
        if self._is_model_available(self.client.default_model):
            logger.warning(f"Fallback model '{fallback_model}' not available, using default '{self.client.default_model}'")
            return self.client.default_model
        
        # Last resort: try to find any available model
        try:
            available_models = self.client.list_models()
            if available_models:
                logger.warning(f"No preferred models available, using '{available_models[0]}'")
                return available_models[0]
        except Exception:
            pass
        
        # Return default even if not available (will fail with proper error)
        return self.client.default_model
    
    def _is_model_available(self, model: str) -> bool:
        """Check if a model is available on the server."""
        if not self.client.check_server():
            return False  # Can't check, assume not available
        
        try:
            available_models = self.client.list_models()
            # Check exact match or base name match
            model_base = model.split(':')[0]
            for available in available_models:
                if available == model or available.startswith(model_base + ':'):
                    return True
            return False
        except Exception:
            return False  # Assume not available if we can't check
    
    def check_available(self) -> bool:
        """Check if Ollama is available and ready."""
        return self.client.check_server()
    
    def get_default_model(self) -> str:
        """Get default model name."""
        return self.client.default_model


def create_ralph_llm_provider() -> Optional[RalphOllamaAdapter]:
    """
    Factory function to create LLM provider based on environment.
    
    This function can be used in Ralph workflow implementations to automatically
    select between Ollama and cloud providers based on configuration.
    
    Returns:
        RalphOllamaAdapter if Ollama is configured, None otherwise
    """
    # Check if Ollama is enabled
    if not is_ollama_enabled():
        return None
    
    # Check if config exists
    config_path = get_config_path()
    if config_path.exists():
        adapter = RalphOllamaAdapter(str(config_path))
        if adapter.check_available():
            return adapter
    
    return None


# Convenience function matching common Ralph workflow patterns
def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    task_type: Optional[str] = None
) -> str:
    """
    Convenience function for LLM calls in Ralph workflow.
    
    This function can be used as a drop-in replacement for cloud API calls.
    It automatically uses Ollama if configured, or falls back to cloud APIs.
    
    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        model: Model name (optional)
        task_type: Task type for model selection (optional)
    
    Returns:
        Generated response text
    """
    # Try Ollama first via factory function (checks env var)
    adapter = create_ralph_llm_provider()
    
    # If factory didn't create adapter, try direct creation if config file exists
    if not adapter:
        config_path = get_config_path()
        if config_path.exists():
            try:
                adapter = RalphOllamaAdapter(str(config_path))
                if adapter.check_available():
                    logger.info("Using Ollama adapter from config file (env var not set)")
                else:
                    adapter = None
            except Exception as e:
                logger.debug(f"Could not create adapter from config file: {e}")
                adapter = None
    
    if adapter:
        result = adapter.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            task_type=task_type
        )
        return result['content']
    
    # Fallback: would use cloud API here
    # For now, raise error to indicate Ollama should be configured
    from lib.config import ENV_PROVIDER, ENV_CONFIG
    raise OllamaConfigError(
        f"Ollama is not configured. To use Ollama, set the following environment variables:\n"
        f"  {ENV_PROVIDER}=ollama\n"
        f"  {ENV_CONFIG}=path/to/ollama-config.json\n"
        f"Or ensure the default config file exists at: {DEFAULT_CONFIG_PATH}"
    )


if __name__ == '__main__':
    # CLI usage example
    if len(sys.argv) < 2:
        print("Usage: ralph_ollama_adapter.py <prompt> [task_type] [model]")
        sys.exit(1)
    
    prompt = sys.argv[1]
    task_type = sys.argv[2] if len(sys.argv) > 2 else None
    model = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        adapter = RalphOllamaAdapter()
        result = adapter.generate(
            prompt=prompt,
            task_type=task_type,
            model=model
        )
        print(result['content'])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
