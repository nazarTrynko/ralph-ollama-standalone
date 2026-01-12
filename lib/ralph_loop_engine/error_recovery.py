#!/usr/bin/env python3
"""
Error Recovery for Ralph Loop Engine
Handles error classification, retry logic, and recovery strategies.
"""

from typing import Optional
from lib.ralph_loop_engine.types import Phase
from lib.logging_config import get_logger

logger = get_logger('error_recovery')


class ErrorRecovery:
    """Manages error recovery and retry logic."""
    
    def __init__(
        self,
        max_retries: int = 2,
        retry_delay: float = 2.0,
        continue_on_non_critical: bool = True
    ):
        """Initialize error recovery.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            continue_on_non_critical: Whether to continue on non-critical errors
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.continue_on_non_critical = continue_on_non_critical
    
    def is_critical_error(self, error: str, phase: Phase) -> bool:
        """Determine if an error is critical (should stop execution).
        
        Args:
            error: Error message
            phase: Current phase
            
        Returns:
            True if error is critical
        """
        # Critical errors that should stop execution
        critical_patterns = [
            'permission denied',
            'disk full',
            'out of memory',
            'connection refused',
            'timeout',
            'authentication failed',
            'invalid api key'
        ]
        
        error_lower = error.lower()
        for pattern in critical_patterns:
            if pattern in error_lower:
                return True
        
        # UPDATE phase errors are usually non-critical (just marking tasks)
        if phase == Phase.UPDATE:
            return False
        
        # Other errors are generally non-critical (can retry or continue)
        return False
    
    def should_retry(
        self,
        error: str,
        phase: Phase,
        retry_count: int
    ) -> bool:
        """Determine if an error should be retried.
        
        Args:
            error: Error message
            phase: Current phase
            retry_count: Current retry attempt count
            
        Returns:
            True if should retry
        """
        # Don't retry if exceeded max retries
        if retry_count >= self.max_retries:
            return False
        
        # Don't retry critical errors
        if self.is_critical_error(error, phase):
            return False
        
        # Retry non-critical errors
        return True
    
    def get_retry_delay(self, retry_count: int) -> float:
        """Get delay before retry.
        
        Args:
            retry_count: Current retry attempt count
            
        Returns:
            Delay in seconds (can implement exponential backoff)
        """
        # Simple linear backoff: delay * (retry_count + 1)
        return self.retry_delay * (retry_count + 1)
    
    def classify_error(self, error: str) -> str:
        """Classify error type.
        
        Args:
            error: Error message
            
        Returns:
            Error classification (e.g., 'network', 'validation', 'permission', etc.)
        """
        error_lower = error.lower()
        
        if any(keyword in error_lower for keyword in ['connection', 'network', 'timeout', 'refused']):
            return 'network'
        elif any(keyword in error_lower for keyword in ['permission', 'access denied', 'forbidden']):
            return 'permission'
        elif any(keyword in error_lower for keyword in ['validation', 'invalid', 'syntax']):
            return 'validation'
        elif any(keyword in error_lower for keyword in ['memory', 'out of memory']):
            return 'resource'
        elif any(keyword in error_lower for keyword in ['authentication', 'api key', 'token']):
            return 'authentication'
        else:
            return 'unknown'
