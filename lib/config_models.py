#!/usr/bin/env python3
"""
Pydantic models for configuration validation.
Simplifies and replaces manual validation in lib/config.py.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class ServerConfig(BaseModel):
    """Server configuration model."""
    baseUrl: str
    port: int = Field(default=11434, ge=1, le=65535)
    timeout: float = Field(default=300.0, gt=0)


class ModelParameters(BaseModel):
    """Model parameters configuration."""
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    topP: Optional[float] = Field(default=None, ge=0, le=1)
    topK: Optional[int] = Field(default=None, ge=1)
    numCtx: Optional[int] = Field(default=None, ge=1)


class ModelConfig(BaseModel):
    """Model configuration."""
    parameters: Optional[ModelParameters] = None


class RetryConfig(BaseModel):
    """Retry configuration."""
    maxAttempts: int = Field(default=3, ge=1)
    backoffSeconds: float = Field(default=1.0, ge=0)


class OllamaConfigModel(BaseModel):
    """Ollama configuration model."""
    server: ServerConfig
    defaultModel: str = Field(min_length=1)
    models: Dict[str, ModelConfig] = Field(default_factory=dict)
    retry: Optional[RetryConfig] = None
    cache: Optional[Dict[str, Any]] = None
    
    @validator('defaultModel')
    def validate_model(cls, v):
        """Validate default model is non-empty."""
        if not v or not v.strip():
            raise ValueError('defaultModel must be non-empty')
        return v.strip()


class TaskConfig(BaseModel):
    """Task configuration."""
    preferredModel: Optional[str] = None
    fallbackModel: Optional[str] = None


class WorkflowConfig(BaseModel):
    """Workflow configuration."""
    tasks: Dict[str, TaskConfig] = Field(default_factory=dict)


class PerformanceConfig(BaseModel):
    """Performance configuration."""
    timeoutSeconds: float = Field(default=300.0, gt=0)


class WorkflowConfigModel(BaseModel):
    """Workflow configuration model."""
    workflow: Optional[WorkflowConfig] = None
    performance: Optional[PerformanceConfig] = None


def validate_ollama_config_pydantic(config_dict: Dict[str, Any]) -> OllamaConfigModel:
    """Validate Ollama config using Pydantic.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        Validated OllamaConfigModel
        
    Raises:
        ValueError: If validation fails
    """
    try:
        return OllamaConfigModel(**config_dict)
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def validate_workflow_config_pydantic(config_dict: Dict[str, Any]) -> WorkflowConfigModel:
    """Validate workflow config using Pydantic.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        Validated WorkflowConfigModel
        
    Raises:
        ValueError: If validation fails
    """
    try:
        return WorkflowConfigModel(**config_dict)
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")
