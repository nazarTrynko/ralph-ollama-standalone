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
from typing import Optional, Dict, Any, List, Union

from .config import get_config_path, load_and_validate_config, ConfigValidationError, ENV_CONFIG
from .exceptions import (
    OllamaError,
    OllamaServerError,
    OllamaConnectionError,
    OllamaModelError,
    OllamaConfigError,
    OllamaTimeoutError,
)
from .logging_config import get_logger

logger = get_logger('client')


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize Ollama client with configuration.
        
        Args:
            config_path: Path to ollama-config.json. If None, uses default or env var.
        """
        if config_path is None:
            self.config_path: Path = get_config_path()
        else:
            self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_config()
        self.base_url: str = self.config['server']['baseUrl']
        self.default_model: str = self.config.get('defaultModel', 'llama3.2')
        
        logger.info(f"Initialized OllamaClient: server={self.base_url}, model={self.default_model}")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load and validate configuration from JSON file."""
        try:
            return load_and_validate_config(self.config_path)
        except ConfigValidationError as e:
            raise OllamaConfigError(
                f"Configuration validation failed: {e}",
                config_path=str(self.config_path)
            ) from e
        except FileNotFoundError as e:
            raise OllamaConfigError(
                f"Configuration file not found: {self.config_path}. "
                f"Please create the config file or set {ENV_CONFIG} environment variable.",
                config_path=str(self.config_path)
            ) from e
    
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
            logger.debug(f"Checking server connection: {self.base_url}")
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            logger.debug("Server connection successful")
            return True
        except (requests.RequestException, Exception) as e:
            logger.debug(f"Server connection failed: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """List available models.
        
        Returns:
            List of model names.
            
        Raises:
            OllamaConnectionError: If server is not accessible
            OllamaServerError: If server returns an error
        """
        try:
            logger.debug("Listing available models")
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            logger.info(f"Found {len(models)} models: {', '.join(models)}")
            return models
        except requests.exceptions.ConnectionError as e:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama server at {self.base_url}. "
                f"Is the server running? Start it with: ollama serve",
                server_url=self.base_url
            ) from e
        except requests.exceptions.Timeout as e:
            raise OllamaTimeoutError(
                f"Request to Ollama server timed out after 10 seconds. "
                f"Server may be slow or unresponsive.",
                timeout=10.0
            ) from e
        except requests.exceptions.HTTPError as e:
            raise OllamaServerError(
                f"Ollama server returned an error: {e}",
                server_url=self.base_url,
                status_code=e.response.status_code if hasattr(e, 'response') else None
            ) from e
        except requests.RequestException as e:
            raise OllamaServerError(
                f"Failed to list models from Ollama server: {e}",
                server_url=self.base_url
            ) from e
    
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
            raise OllamaConnectionError(
                f"Ollama server is not running at {self.base_url}. "
                "Start the server with: ollama serve",
                server_url=self.base_url
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
        logger.info(f"Generating response with model '{model}' (attempts: {max_attempts})")
        if logger.log_requests if hasattr(logger, 'log_requests') else False:
            logger.debug(f"Request body: {json.dumps(body, indent=2)}")
        
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    logger.debug(f"Retry attempt {attempt + 1}/{max_attempts}")
                
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=body,
                    timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
                
                if logger.log_responses if hasattr(logger, 'log_responses') else False:
                    logger.debug(f"Response: {json.dumps(data, indent=2)}")
                
                # Check for model errors in response
                if 'error' in data:
                    error_msg = data.get('error', 'Unknown error')
                    if 'model' in error_msg.lower() or 'not found' in error_msg.lower():
                        available_models = []
                        try:
                            available_models = self.list_models()
                        except Exception:
                            pass
                        raise OllamaModelError(
                            f"Model error: {error_msg}",
                            model=model,
                            available_models=available_models
                        )
                    else:
                        raise OllamaServerError(
                            f"Ollama server error: {error_msg}",
                            server_url=self.base_url
                        )
                
                result = {
                    "response": data.get('response', ''),
                    "model": model,
                    "tokens": {
                        "prompt": data.get('prompt_eval_count', 0),
                        "completion": data.get('eval_count', 0),
                        "total": data.get('prompt_eval_count', 0) + data.get('eval_count', 0)
                    },
                    "done": data.get('done', True)
                }
                logger.info(f"Generation successful: {result['tokens']['total']} tokens")
                return result
            except OllamaModelError:
                # Don't retry model errors
                raise
            except requests.exceptions.ConnectionError as e:
                last_error = OllamaConnectionError(
                    f"Cannot connect to Ollama server at {self.base_url}. "
                    f"Is the server running? Start it with: ollama serve",
                    server_url=self.base_url
                )
                if attempt < max_attempts - 1:
                    wait_time = backoff_ms
                    if exponential:
                        wait_time = backoff_ms * (2 ** attempt)
                    time.sleep(wait_time / 1000.0)
            except requests.exceptions.Timeout as e:
                last_error = OllamaTimeoutError(
                    f"Request to Ollama server timed out after {timeout} seconds. "
                    f"Server may be slow or unresponsive. Try increasing timeout in config.",
                    timeout=float(timeout)
                )
                if attempt < max_attempts - 1:
                    wait_time = backoff_ms
                    if exponential:
                        wait_time = backoff_ms * (2 ** attempt)
                    time.sleep(wait_time / 1000.0)
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else None
                if status_code == 404:
                    # Model not found
                    available_models = []
                    try:
                        available_models = self.list_models()
                    except Exception:
                        pass
                    raise OllamaModelError(
                        f"Model '{model}' not found on Ollama server",
                        model=model,
                        available_models=available_models
                    )
                last_error = OllamaServerError(
                    f"Ollama server returned HTTP error: {e}",
                    server_url=self.base_url,
                    status_code=status_code
                )
                if attempt < max_attempts - 1:
                    wait_time = backoff_ms
                    if exponential:
                        wait_time = backoff_ms * (2 ** attempt)
                    time.sleep(wait_time / 1000.0)
            except requests.RequestException as e:
                last_error = OllamaServerError(
                    f"Request to Ollama server failed: {e}",
                    server_url=self.base_url
                )
                if attempt < max_attempts - 1:
                    wait_time = backoff_ms
                    if exponential:
                        wait_time = backoff_ms * (2 ** attempt)
                    time.sleep(wait_time / 1000.0)
        
        # All retries exhausted
        logger.error(f"Generation failed after {max_attempts} attempts: {last_error}")
        raise OllamaError(
            f"Failed to generate response after {max_attempts} attempts. "
            f"Last error: {last_error}"
        ) from last_error
    
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
