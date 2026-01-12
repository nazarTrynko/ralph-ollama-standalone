"""
Unit tests for RalphOllamaAdapter.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from integration.ralph_ollama_adapter import (
    RalphOllamaAdapter,
    create_ralph_llm_provider,
    call_llm,
)
from lib.exceptions import OllamaConfigError, OllamaConnectionError


class TestRalphOllamaAdapter:
    """Test RalphOllamaAdapter."""
    
    def test_init_default(self):
        """Test adapter initialization with default config."""
        adapter = RalphOllamaAdapter()
        assert adapter.client is not None
        assert adapter.config_path is None
    
    def test_init_custom_config(self, tmp_path):
        """Test adapter initialization with custom config."""
        config_file = tmp_path / 'custom-config.json'
        config_data = {
            'server': {
                'baseUrl': 'http://localhost:11434',
                'timeout': 300
            },
            'defaultModel': 'codellama'
        }
        config_file.write_text(json.dumps(config_data))
        
        adapter = RalphOllamaAdapter(str(config_file))
        assert adapter.config_path == str(config_file)
    
    def test_generate_basic(self, mock_ollama_server):
        """Test basic generation."""
        adapter = RalphOllamaAdapter()
        result = adapter.generate("Hello", model="llama3.2")
        
        assert 'content' in result
        assert 'model' in result
        assert 'provider' in result
        assert 'tokens' in result
        assert result['provider'] == 'ollama'
    
    def test_generate_with_task_type(self, mock_ollama_server):
        """Test generation with task type."""
        adapter = RalphOllamaAdapter()
        result = adapter.generate("Hello", task_type="implementation")
        
        assert 'content' in result
        # Should auto-select model based on task type
        assert 'model' in result
    
    def test_generate_with_system_prompt(self, mock_ollama_server):
        """Test generation with system prompt."""
        adapter = RalphOllamaAdapter()
        result = adapter.generate(
            "Hello",
            system_prompt="You are helpful",
            model="llama3.2"
        )
        assert 'content' in result
    
    def test_select_model_for_task(self):
        """Test model selection for task type."""
        adapter = RalphOllamaAdapter()
        
        # Test with known task types
        model = adapter._select_model_for_task('implementation')
        assert model in ['codellama', adapter.client.default_model]
        
        model = adapter._select_model_for_task('testing')
        assert model in ['llama3.2', adapter.client.default_model]
        
        # Test with unknown task type (should use default)
        model = adapter._select_model_for_task('unknown')
        assert model == adapter.client.default_model
    
    def test_check_available(self):
        """Test availability check."""
        adapter = RalphOllamaAdapter()
        with patch.object(adapter.client, 'check_server', return_value=True):
            assert adapter.check_available() is True
        
        with patch.object(adapter.client, 'check_server', return_value=False):
            assert adapter.check_available() is False
    
    def test_get_default_model(self):
        """Test getting default model."""
        adapter = RalphOllamaAdapter()
        model = adapter.get_default_model()
        assert isinstance(model, str)
        assert model == adapter.client.default_model


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_ralph_llm_provider_enabled(self, monkeypatch):
        """Test provider creation when Ollama is enabled."""
        monkeypatch.setenv('RALPH_LLM_PROVIDER', 'ollama')
        
        with patch('integration.ralph_ollama_adapter.get_config_path') as mock_path:
            mock_path.return_value = Path(__file__).parent.parent / 'config' / 'ollama-config.json'
            
            with patch('integration.ralph_ollama_adapter.RalphOllamaAdapter') as mock_adapter:
                mock_instance = Mock()
                mock_instance.check_available.return_value = True
                mock_adapter.return_value = mock_instance
                
                provider = create_ralph_llm_provider()
                # Should return adapter if available
                assert provider is not None
    
    def test_create_ralph_llm_provider_disabled(self, monkeypatch):
        """Test provider creation when Ollama is disabled."""
        monkeypatch.setenv('RALPH_LLM_PROVIDER', 'openai')
        
        provider = create_ralph_llm_provider()
        assert provider is None
    
    def test_create_ralph_llm_provider_not_available(self, monkeypatch):
        """Test provider creation when Ollama is not available."""
        monkeypatch.setenv('RALPH_LLM_PROVIDER', 'ollama')
        
        with patch('integration.ralph_ollama_adapter.get_config_path') as mock_path:
            mock_path.return_value = Path(__file__).parent.parent / 'config' / 'ollama-config.json'
            
            with patch('integration.ralph_ollama_adapter.RalphOllamaAdapter') as mock_adapter:
                mock_instance = Mock()
                mock_instance.check_available.return_value = False
                mock_adapter.return_value = mock_instance
                
                provider = create_ralph_llm_provider()
                # Should return None if not available
                assert provider is None


class TestCallLLM:
    """Test call_llm convenience function."""
    
    def test_call_llm_success(self, mock_ollama_server, monkeypatch):
        """Test successful LLM call."""
        monkeypatch.setenv('RALPH_LLM_PROVIDER', 'ollama')
        
        response = call_llm("Hello", model="llama3.2")
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_call_llm_not_configured(self, monkeypatch):
        """Test LLM call when Ollama is not configured."""
        monkeypatch.setenv('RALPH_LLM_PROVIDER', 'openai')
        
        with pytest.raises(OllamaConfigError):
            call_llm("Hello")
    
    def test_call_llm_with_task_type(self, mock_ollama_server, monkeypatch):
        """Test LLM call with task type."""
        monkeypatch.setenv('RALPH_LLM_PROVIDER', 'ollama')
        
        response = call_llm("Hello", task_type="implementation")
        assert isinstance(response, str)
    
    def test_call_llm_with_system_prompt(self, mock_ollama_server, monkeypatch):
        """Test LLM call with system prompt."""
        monkeypatch.setenv('RALPH_LLM_PROVIDER', 'ollama')
        
        response = call_llm(
            "Hello",
            system_prompt="You are helpful",
            model="llama3.2"
        )
        assert isinstance(response, str)
