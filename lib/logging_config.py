"""
Logging configuration for Ralph Ollama integration.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Default log format
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logging(
    level: str = 'INFO',
    log_path: Optional[Path] = None,
    log_requests: bool = False,
    log_responses: bool = False,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_path: Optional path to log file
        log_requests: Whether to log requests
        log_responses: Whether to log responses
        format_string: Custom format string
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('ralph_ollama')
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        format_string or DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_path specified)
    if log_path:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Store configuration
    logger.log_requests = log_requests
    logger.log_responses = log_responses
    
    return logger


def setup_logging_from_config(config: Dict[str, Any]) -> logging.Logger:
    """
    Set up logging from configuration dictionary.
    
    Args:
        config: Configuration dictionary with 'logging' section
        
    Returns:
        Configured logger instance
    """
    logging_config = config.get('logging', {})
    
    if not logging_config.get('enabled', True):
        # Disable logging
        logger = logging.getLogger('ralph_ollama')
        logger.disabled = True
        return logger
    
    level = logging_config.get('level', 'info').upper()
    log_path = logging_config.get('logPath')
    log_requests = logging_config.get('logRequests', False)
    log_responses = logging_config.get('logResponses', False)
    
    if log_path:
        log_path = Path(log_path)
    
    return setup_logging(
        level=level,
        log_path=log_path,
        log_requests=log_requests,
        log_responses=log_responses
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get logger instance.
    
    Args:
        name: Optional logger name (defaults to 'ralph_ollama')
        
    Returns:
        Logger instance with default attributes set
    """
    if name:
        logger = logging.getLogger(f'ralph_ollama.{name}')
    else:
        logger = logging.getLogger('ralph_ollama')
    
    # Ensure logger has default attributes if not set
    if not hasattr(logger, 'log_requests'):
        logger.log_requests = False
    if not hasattr(logger, 'log_responses'):
        logger.log_responses = False
    
    return logger
