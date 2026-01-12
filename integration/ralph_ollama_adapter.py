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

# Add project root to path to enable package imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from lib.ollama_client import OllamaClient
from lib.config import is_ollama_enabled, get_config_path, DEFAULT_CONFIG_PATH


class RalphOllamaAdapter:
    """
    Adapter that makes OllamaClient compatible with Ralph workflow patterns.
    
    This adapter provides a standardized interface that can be used as a drop-in
    replacement for cloud-based LLM providers in Ralph workflow implementations.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize adapter with Ollama configuration."""
        self.client = OllamaClient(config_path)
        self.config_path = config_path
        
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        task_type: Optional[str] = None,
        **kwargs
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
        
        # Generate response
        result = self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            **kwargs
        )
        
        # Format response to match Ralph workflow expectations
        return {
            'content': result['response'],
            'model': result['model'],
            'provider': 'ollama',
            'tokens': result.get('tokens', {}),
            'done': result.get('done', True)
        }
    
    def _select_model_for_task(self, task_type: str) -> str:
        """Select appropriate model for task type."""
        # Load workflow config to get task-based model selection
        try:
            workflow_config_path = Path(__file__).parent.parent / 'config' / 'workflow-config.json'
            if workflow_config_path.exists():
                import json
                with open(workflow_config_path) as f:
                    config = json.load(f)
                
                tasks = config.get('workflow', {}).get('tasks', {})
                task_config = tasks.get(task_type, {})
                return task_config.get('preferredModel') or self.client.default_model
        except Exception:
            pass
        
        # Fallback: simple mapping
        model_map = {
            'implementation': 'codellama',
            'code-review': 'codellama',
            'refactoring': 'codellama',
            'testing': 'llama3.2',
            'documentation': 'llama3.2',
        }
        
        return model_map.get(task_type, self.client.default_model)
    
    def check_available(self) -> bool:
        """Check if Ollama is available and ready."""
        return self.client.check_server()
    
    def get_default_model(self) -> str:
        """Get default model name."""
        return self.client.default_model


def create_ralph_llm_provider():
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
    # Try Ollama first
    adapter = create_ralph_llm_provider()
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
    raise RuntimeError(
        f"Ollama not configured. Set {ENV_PROVIDER}=ollama and "
        f"{ENV_CONFIG} environment variables."
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
