#!/usr/bin/env python3
"""
Ollama Client for Ralph Workflow
Provides a simple interface to Ollama API for Ralph workflow integration.
"""

import os
import json
import requests
import time
from pathlib import Path
from typing import Optional, Dict, Any

from .config import get_config_path


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize Ollama client with configuration.
        
        Args:
            config_path: Path to ollama-config.json. If None, uses default or env var.
        """
        if config_path is None:
            self.config_path = get_config_path()
        else:
            self.config_path = Path(config_path)
        self.config = self._load_config()
        self.base_url = self.config['server']['baseUrl']
        self.default_model = self.config.get('defaultModel', 'llama3.2')
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path) as f:
            return json.load(f)
    
    def _get_model_params(self, model: str) -> Dict[str, Any]:
        """Get parameters for a specific model."""
        models = self.config.get('models', {})
        if model in models:
            return models[model].get('parameters', {})
        return {}
    
    def check_server(self) -> bool:
        """Check if Ollama server is running.
        
        Returns:
            True if server is accessible, False otherwise.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            return True
        except (requests.RequestException, Exception):
            return False
    
    def list_models(self) -> list:
        """List available models.
        
        Returns:
            List of model names.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to list models: {e}")
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response from Ollama.
        
        Args:
            prompt: The user prompt.
            model: Model name. If None, uses default.
            system_prompt: Optional system prompt.
            stream: Whether to stream the response.
            **kwargs: Additional parameters (temperature, etc.)
        
        Returns:
            Dictionary with 'response', 'model', 'tokens', etc.
        """
        if model is None:
            model = self.default_model
        
        # Check server
        if not self.check_server():
            raise RuntimeError(
                f"Ollama server not running at {self.base_url}. "
                "Start with: ollama serve"
            )
        
        # Build full prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Get model parameters
        model_params = self._get_model_params(model)
        
        # Merge parameters (kwargs override config)
        params = {**model_params, **kwargs}
        
        # Build request body
        body = {
            "model": model,
            "prompt": full_prompt,
            "stream": stream,
            "options": params
        }
        
        # Get timeout from config
        timeout = self.config.get('server', {}).get('timeout', 300)
        
        # Make request with retry logic
        retry_config = self.config.get('retry', {})
        max_attempts = retry_config.get('maxAttempts', 3)
        backoff_ms = retry_config.get('backoffMs', 1000)
        exponential = retry_config.get('exponentialBackoff', True)
        
        last_error = None
        for attempt in range(max_attempts):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=body,
                    timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "response": data.get('response', ''),
                    "model": model,
                    "tokens": {
                        "prompt": data.get('prompt_eval_count', 0),
                        "completion": data.get('eval_count', 0),
                        "total": data.get('prompt_eval_count', 0) + data.get('eval_count', 0)
                    },
                    "done": data.get('done', True)
                }
            except requests.RequestException as e:
                last_error = e
                if attempt < max_attempts - 1:
                    wait_time = backoff_ms
                    if exponential:
                        wait_time = backoff_ms * (2 ** attempt)
                    time.sleep(wait_time / 1000.0)
        
        raise RuntimeError(f"Failed after {max_attempts} attempts: {last_error}")
    
    def test_model(self, model: Optional[str] = None) -> bool:
        """Test if a model works.
        
        Args:
            model: Model name. If None, uses default.
        
        Returns:
            True if model works, False otherwise.
        """
        try:
            result = self.generate(
                prompt="Say hello in one word.",
                model=model
            )
            return bool(result.get('response'))
        except Exception:
            return False


def get_llm_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    config_path: Optional[str] = None
) -> str:
    """Convenience function for getting LLM response.
    
    This function can be used as a drop-in replacement for cloud API calls.
    
    Args:
        prompt: The user prompt.
        system_prompt: Optional system prompt.
        model: Model name. If None, uses default from config.
        config_path: Path to config file. If None, uses default or env var.
    
    Returns:
        The generated response text.
    """
    client = OllamaClient(config_path)
    result = client.generate(prompt, model=model, system_prompt=system_prompt)
    return result['response']


if __name__ == '__main__':
    # CLI usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: ollama_client.py <prompt> [model]")
        sys.exit(1)
    
    prompt = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        client = OllamaClient()
        result = client.generate(prompt, model=model)
        print(result['response'])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
