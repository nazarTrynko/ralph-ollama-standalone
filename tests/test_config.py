"""
Tests for configuration loading and validation.
"""

import pytest
import json
import tempfile
from pathlib import Path
from lib.config import (
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
)
import os


class TestConfigPaths:
    """Test configuration path utilities."""
    
    def test_get_config_path_default(self):
        """Test default config path."""
        path = get_config_path()
        assert isinstance(path, Path)
        assert path.name == 'ollama-config.json'
    
    def test_get_config_path_env_var(self, monkeypatch):
        """Test config path from environment variable."""
        test_path = '/tmp/test-config.json'
        monkeypatch.setenv(ENV_CONFIG, test_path)
        path = get_config_path()
        assert str(path) == test_path
    
    def test_get_workflow_config_path_default(self):
        """Test default workflow config path."""
        path = get_workflow_config_path()
        assert isinstance(path, Path)
        assert path.name == 'workflow-config.json'
    
    def test_get_default_model(self, monkeypatch):
        """Test default model retrieval."""
        # Test default
        model = get_default_model()
        assert model == 'llama3.2'
        
        # Test from env
        monkeypatch.setenv('RALPH_LLM_MODEL', 'codellama')
        model = get_default_model()
        assert model == 'codellama'
    
    def test_is_ollama_enabled(self, monkeypatch):
        """Test Ollama enabled check."""
        # Test default (not enabled)
        assert not is_ollama_enabled()
        
        # Test enabled
        monkeypatch.setenv(ENV_PROVIDER, 'ollama')
        assert is_ollama_enabled()
        
        # Test case insensitive
        monkeypatch.setenv(ENV_PROVIDER, 'OLLAMA')
        assert is_ollama_enabled()


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_validate_ollama_config_valid(self):
        """Test validation of valid config."""
        config = {
            'server': {
                'baseUrl': 'http://localhost:11434',
                'port': 11434,
                'timeout': 300
            },
            'defaultModel': 'llama3.2',
            'models': {
                'llama3.2': {
                    'parameters': {
                        'temperature': 0.7
                    }
                }
            }
        }
        warnings = validate_ollama_config(config)
        assert isinstance(warnings, list)
    
    def test_validate_ollama_config_missing_required(self):
        """Test validation fails on missing required keys."""
        config = {
            'server': {
                'baseUrl': 'http://localhost:11434'
            }
            # Missing defaultModel
        }
        with pytest.raises(ConfigValidationError):
            validate_ollama_config(config)
    
    def test_validate_ollama_config_invalid_port(self):
        """Test validation warns on invalid port."""
        config = {
            'server': {
                'baseUrl': 'http://localhost:11434',
                'port': 99999  # Invalid port
            },
            'defaultModel': 'llama3.2'
        }
        warnings = validate_ollama_config(config)
        assert len(warnings) > 0
        assert any('port' in w.lower() for w in warnings)
    
    def test_validate_ollama_config_invalid_temperature(self):
        """Test validation warns on invalid temperature."""
        config = {
            'server': {
                'baseUrl': 'http://localhost:11434'
            },
            'defaultModel': 'llama3.2',
            'models': {
                'llama3.2': {
                    'parameters': {
                        'temperature': 5.0  # Invalid (should be 0-2)
                    }
                }
            }
        }
        warnings = validate_ollama_config(config)
        assert len(warnings) > 0
        assert any('temperature' in w.lower() for w in warnings)
    
    def test_validate_workflow_config_valid(self):
        """Test validation of valid workflow config."""
        config = {
            'workflow': {
                'tasks': {
                    'implementation': {
                        'preferredModel': 'codellama'
                    }
                }
            }
        }
        warnings = validate_workflow_config(config)
        assert isinstance(warnings, list)


class TestLoadAndValidateConfig:
    """Test loading and validating config files."""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading a valid config file."""
        config_file = tmp_path / 'test-config.json'
        config_data = {
            'server': {
                'baseUrl': 'http://localhost:11434'
            },
            'defaultModel': 'llama3.2'
        }
        config_file.write_text(json.dumps(config_data))
        
        loaded = load_and_validate_config(config_file)
        assert loaded['defaultModel'] == 'llama3.2'
        assert loaded['server']['baseUrl'] == 'http://localhost:11434'
    
    def test_load_missing_file(self, tmp_path):
        """Test loading non-existent config file."""
        config_file = tmp_path / 'nonexistent.json'
        with pytest.raises(FileNotFoundError):
            load_and_validate_config(config_file)
    
    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON."""
        config_file = tmp_path / 'invalid.json'
        config_file.write_text('{ invalid json }')
        
        with pytest.raises(ConfigValidationError):
            load_and_validate_config(config_file)
    
    def test_load_invalid_config(self, tmp_path):
        """Test loading config that fails validation."""
        config_file = tmp_path / 'invalid-config.json'
        config_data = {
            'server': {
                'baseUrl': 'http://localhost:11434'
            }
            # Missing defaultModel
        }
        config_file.write_text(json.dumps(config_data))
        
        with pytest.raises(ConfigValidationError):
            load_and_validate_config(config_file)
