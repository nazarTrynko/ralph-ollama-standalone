#!/usr/bin/env python3
"""
Status Logger for Ralph Loop Engine
Handles status logging and callback management.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from lib.ralph_loop_engine.types import Phase
from lib.logging_config import get_logger

logger = get_logger('status_logger')


class StatusLogger:
    """Manages status logging and callbacks."""
    
    def __init__(self, progress_tracker: Any):
        """Initialize status logger.
        
        Args:
            progress_tracker: ProgressTracker instance for progress calculations
        """
        self.progress_tracker = progress_tracker
        self.status_log: List[Dict[str, Any]] = []
        self.status_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    
    def set_callback(self, callback: Optional[Callable[[Dict[str, Any]], None]]) -> None:
        """Set status callback function.
        
        Args:
            callback: Callback function to call on status updates
        """
        self.status_callback = callback
    
    def log(
        self,
        message: str,
        phase: Phase,
        current_phase: Phase,
        **kwargs: Any
    ) -> None:
        """Log status message with progress information.
        
        Args:
            message: Status message
            phase: Phase for this log entry (optional, uses current_phase if None)
            current_phase: Current phase for progress calculation
            **kwargs: Additional status data
        """
        log_phase = phase if phase else current_phase
        phase_progress = self.progress_tracker.calculate_phase_progress(log_phase)
        task_progress = self.progress_tracker.calculate_task_progress(current_phase)
        time_remaining = self.progress_tracker.estimate_time_remaining(log_phase)
        
        status_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'phase': log_phase.value,
            'phase_progress': round(phase_progress, 2),
            'task_progress': round(task_progress, 2),
            'time_remaining': round(time_remaining, 1) if time_remaining else None,
            'files_created': self.progress_tracker.files_created_count,
            'files_expected': self.progress_tracker.files_expected if self.progress_tracker.files_expected > 0 else None,
            **kwargs
        }
        self.status_log.append(status_entry)
        logger.info(f"[{status_entry['phase']}] {message} (Progress: {int(task_progress * 100)}%)")
        self.emit(status_entry)
    
    def emit(self, status: Dict[str, Any]) -> None:
        """Emit status update to callback if set.
        
        Args:
            status: Status dictionary
        """
        if self.status_callback:
            try:
                self.status_callback(status)
            except Exception as e:
                logger.warning(f"Error in status callback: {e}")
    
    def get_status_log(self) -> List[Dict[str, Any]]:
        """Get status log.
        
        Returns:
            List of status entries
        """
        return self.status_log.copy()
    
    def clear_status_log(self) -> None:
        """Clear status log."""
        self.status_log.clear()
