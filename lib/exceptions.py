"""
Custom exception classes for Ralph Ollama integration.
"""


class OllamaError(Exception):
    """Base exception for all Ollama-related errors."""
    pass


class OllamaServerError(OllamaError):
    """Raised when Ollama server is unavailable or returns an error."""
    
    def __init__(self, message: str, server_url: str = None, status_code: int = None):
        super().__init__(message)
        self.server_url = server_url
        self.status_code = status_code
    
    def __str__(self) -> str:
        msg = super().__str__()
        if self.server_url:
            msg += f" (Server: {self.server_url})"
        if self.status_code:
            msg += f" (Status: {self.status_code})"
        return msg


class OllamaConnectionError(OllamaError):
    """Raised when connection to Ollama server fails."""
    
    def __init__(self, message: str, server_url: str = None):
        super().__init__(message)
        self.server_url = server_url
    
    def __str__(self) -> str:
        msg = super().__str__()
        if self.server_url:
            msg += f" (Server: {self.server_url})"
        if "not running" in msg.lower() or "connection" in msg.lower():
            msg += "\n  To fix: Start Ollama server with 'ollama serve'"
        return msg


class OllamaModelError(OllamaError):
    """Raised when model-related errors occur."""
    
    def __init__(self, message: str, model: str = None, available_models: list = None):
        super().__init__(message)
        self.model = model
        self.available_models = available_models
    
    def __str__(self) -> str:
        msg = super().__str__()
        if self.model:
            msg += f" (Model: {self.model})"
        if self.available_models:
            msg += f"\n  Available models: {', '.join(self.available_models)}"
        if "not found" in msg.lower():
            msg += "\n  To fix: Pull the model with 'ollama pull <model-name>'"
        return msg


class OllamaConfigError(OllamaError):
    """Raised when configuration errors occur."""
    
    def __init__(self, message: str, config_path: str = None):
        super().__init__(message)
        self.config_path = config_path
    
    def __str__(self) -> str:
        msg = super().__str__()
        if self.config_path:
            msg += f" (Config: {self.config_path})"
        return msg


class OllamaTimeoutError(OllamaError):
    """Raised when request times out."""
    
    def __init__(self, message: str, timeout: float = None):
        super().__init__(message)
        self.timeout = timeout
    
    def __str__(self) -> str:
        msg = super().__str__()
        if self.timeout:
            msg += f" (Timeout: {self.timeout}s)"
        msg += "\n  To fix: Increase timeout in config or check server performance"
        return msg
