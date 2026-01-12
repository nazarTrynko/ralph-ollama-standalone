"""
Unit tests for OllamaClient.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from lib.ollama_client import OllamaClient, get_llm_response
from lib.exceptions import (
    OllamaConnectionError,
    OllamaServerError,
    OllamaModelError,
    OllamaConfigError,
    OllamaTimeoutError,
)


class TestOllamaClientInit:
    """Test OllamaClient initialization."""
    
    def test_init_default_config(self):
        """Test initialization with default config."""
        client = OllamaClient()
        assert client.config_path.exists()
        assert client.base_url is not None
        assert client.default_model is not None
    
    def test_init_custom_config_path(self, tmp_path):
        """Test initialization with custom config path."""
        config_file = tmp_path / 'custom-config.json'
        config_data = {
            'server': {
                'baseUrl': 'http://localhost:11434',
                'timeout': 300
            },
            'defaultModel': 'codellama'
        }
        config_file.write_text(json.dumps(config_data))
        
        client = OllamaClient(str(config_file))
        assert client.config_path == config_file
        assert client.default_model == 'codellama'
    
    def test_init_missing_config(self, tmp_path):
        """Test initialization with missing config file."""
        config_file = tmp_path / 'missing.json'
        with pytest.raises(OllamaConfigError):
            OllamaClient(str(config_file))
    
    def test_init_invalid_config(self, tmp_path):
        """Test initialization with invalid config."""
        config_file = tmp_path / 'invalid.json'
        config_file.write_text('{ invalid json }')
        
        with pytest.raises(OllamaConfigError):
            OllamaClient(str(config_file))


class TestOllamaClientServer:
    """Test server connection methods."""
    
    def test_check_server_success(self, mock_ollama_server):
        """Test successful server check."""
        client = OllamaClient()
        assert client.check_server() is True
    
    def test_check_server_failure(self):
        """Test failed server check."""
        with patch('lib.ollama_client.requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            client = OllamaClient()
            assert client.check_server() is False
    
    def test_list_models_success(self, mock_ollama_server):
        """Test successful model listing."""
        client = OllamaClient()
        models = client.list_models()
        assert isinstance(models, list)
        assert len(models) > 0
    
    def test_list_models_connection_error(self):
        """Test list_models with connection error."""
        with patch('lib.ollama_client.requests.get') as mock_get:
            import requests
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            client = OllamaClient()
            with pytest.raises(OllamaConnectionError):
                client.list_models()
    
    def test_list_models_timeout(self):
        """Test list_models with timeout."""
        with patch('lib.ollama_client.requests.get') as mock_get:
            import requests
            mock_get.side_effect = requests.exceptions.Timeout("Timeout")
            client = OllamaClient()
            with pytest.raises(OllamaTimeoutError):
                client.list_models()
    
    def test_list_models_server_error(self):
        """Test list_models with server error."""
        with patch('lib.ollama_client.requests.get') as mock_get:
            import requests
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError()
            
            client = OllamaClient()
            with pytest.raises(OllamaServerError):
                client.list_models()


class TestOllamaClientGenerate:
    """Test generation methods."""
    
    def test_generate_success(self, mock_ollama_server):
        """Test successful generation."""
        client = OllamaClient()
        result = client.generate("Hello", model="llama3.2")
        
        assert 'response' in result
        assert 'model' in result
        assert 'tokens' in result
        assert result['model'] == 'llama3.2'
    
    def test_generate_with_system_prompt(self, mock_ollama_server):
        """Test generation with system prompt."""
        client = OllamaClient()
        result = client.generate(
            "Hello",
            system_prompt="You are a helpful assistant",
            model="llama3.2"
        )
        assert 'response' in result
    
    def test_generate_server_not_running(self):
        """Test generation when server is not running."""
        client = OllamaClient()
        with patch.object(client, 'check_server', return_value=False):
            with pytest.raises(OllamaConnectionError):
                client.generate("Hello")
    
    def test_generate_model_not_found(self):
        """Test generation with non-existent model."""
        with patch.object(OllamaClient, 'check_server', return_value=True):
            with patch('lib.ollama_client.requests.post') as mock_post:
                import requests
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
                mock_post.return_value = mock_response
                
                client = OllamaClient()
                with patch.object(client, 'list_models', return_value=['llama3.2']):
                    with pytest.raises(OllamaModelError) as exc_info:
                        client.generate("Hello", model="nonexistent")
                    assert exc_info.value.model == "nonexistent"
    
    def test_generate_connection_error(self):
        """Test generation with connection error."""
        with patch.object(OllamaClient, 'check_server', return_value=True):
            with patch('lib.ollama_client.requests.post') as mock_post:
                import requests
                mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
                
                client = OllamaClient()
                # Should retry and eventually raise error
                with pytest.raises(OllamaError):
                    client.generate("Hello")
    
    def test_generate_timeout(self):
        """Test generation with timeout."""
        with patch.object(OllamaClient, 'check_server', return_value=True):
            with patch('lib.ollama_client.requests.post') as mock_post:
                import requests
                mock_post.side_effect = requests.exceptions.Timeout("Timeout")
                
                client = OllamaClient()
                # Should retry and eventually raise error
                with pytest.raises(OllamaError):
                    client.generate("Hello")
    
    def test_generate_uses_default_model(self, mock_ollama_server):
        """Test that default model is used when not specified."""
        client = OllamaClient()
        result = client.generate("Hello")
        assert result['model'] == client.default_model
    
    def test_get_model_params(self):
        """Test getting model parameters."""
        client = OllamaClient()
        params = client._get_model_params('llama3.2')
        # Should return dict (may be empty if model not in config)
        assert isinstance(params, dict)
    
    def test_test_model(self, mock_ollama_server):
        """Test model testing."""
        client = OllamaClient()
        result = client.test_model('llama3.2')
        assert isinstance(result, bool)


class TestConvenienceFunction:
    """Test convenience function."""
    
    def test_get_llm_response(self, mock_ollama_server):
        """Test get_llm_response convenience function."""
        response = get_llm_response("Hello", model="llama3.2")
        assert isinstance(response, str)
        assert len(response) > 0
