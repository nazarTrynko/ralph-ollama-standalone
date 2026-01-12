"""
Ralph Ollama Integration Adapter
Provides high-level adapter for Ralph workflow integration.
"""

from .ralph_ollama_adapter import (
    RalphOllamaAdapter,
    create_ralph_llm_provider,
    call_llm,
)

__all__ = [
    'RalphOllamaAdapter',
    'create_ralph_llm_provider',
    'call_llm',
]
