#!/usr/bin/env python3
"""
Progress Tracker for Ralph Loop Engine
Tracks and calculates progress for phases and tasks.
"""

from typing import Dict, Optional
from datetime import datetime
from lib.ralph_loop_engine.types import Phase


class ProgressTracker:
    """Tracks progress for phases and tasks."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.phase_start_time: Optional[datetime] = None
        self.task_start_time: Optional[datetime] = None
        self.current_phase_progress: float = 0.0
        self.files_expected: int = 0
        self.files_created_count: int = 0
        self.phase_durations: Dict[str, list[float]] = {}
        self.phase_history: list[Dict] = []
    
    def start_phase(self, phase: Phase) -> None:
        """Start tracking a phase.
        
        Args:
            phase: Phase to start tracking
        """
        self.phase_start_time = datetime.now()
        self.current_phase_progress = 0.0
    
    def start_task(self) -> None:
        """Start tracking a task."""
        self.task_start_time = datetime.now()
    
    def set_files_expected(self, count: int) -> None:
        """Set expected number of files.
        
        Args:
            count: Expected number of files
        """
        self.files_expected = count
        self.files_created_count = 0
    
    def increment_files_created(self) -> None:
        """Increment count of files created."""
        self.files_created_count += 1
    
    def record_phase_completion(self, phase: Phase, duration: float) -> None:
        """Record phase completion with duration.
        
        Args:
            phase: Completed phase
            duration: Duration in seconds
        """
        phase_name = phase.value
        if phase_name not in self.phase_durations:
            self.phase_durations[phase_name] = []
        self.phase_durations[phase_name].append(duration)
        # Keep only last 10 durations per phase
        if len(self.phase_durations[phase_name]) > 10:
            self.phase_durations[phase_name] = self.phase_durations[phase_name][-10:]
    
    def calculate_phase_progress(self, phase: Phase) -> float:
        """Calculate progress for a specific phase.
        
        Args:
            phase: Phase to calculate progress for
            
        Returns:
            Progress value between 0.0 and 1.0
        """
        if phase == Phase.STUDY:
            # Study phase: time-based
            if self.phase_start_time:
                elapsed = (datetime.now() - self.phase_start_time).total_seconds()
                avg_duration = self.get_average_duration(phase.value)
                if avg_duration > 0:
                    return min(0.9, elapsed / avg_duration)
            return 0.3
        elif phase == Phase.IMPLEMENT:
            # Implement phase: file-based if files expected, else time-based
            if self.files_expected > 0:
                return min(0.9, self.files_created_count / self.files_expected)
            elif self.phase_start_time:
                elapsed = (datetime.now() - self.phase_start_time).total_seconds()
                avg_duration = self.get_average_duration(phase.value)
                if avg_duration > 0:
                    return min(0.9, elapsed / avg_duration)
            return 0.4
        elif phase == Phase.TEST:
            # Test phase: time-based
            if self.phase_start_time:
                elapsed = (datetime.now() - self.phase_start_time).total_seconds()
                avg_duration = self.get_average_duration(phase.value)
                if avg_duration > 0:
                    return min(0.9, elapsed / avg_duration)
            return 0.5
        elif phase == Phase.UPDATE:
            # Update phase: quick, usually 80% done immediately
            return 0.8
        return 0.0
    
    def get_average_duration(self, phase_name: str) -> float:
        """Get average duration for a phase based on history.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Average duration in seconds, or 0 if no history
        """
        if phase_name not in self.phase_durations or not self.phase_durations[phase_name]:
            # Default estimates (in seconds)
            defaults = {
                'study': 30.0,
                'implement': 60.0,
                'test': 20.0,
                'update': 5.0
            }
            return defaults.get(phase_name, 30.0)
        
        durations = self.phase_durations[phase_name]
        return sum(durations) / len(durations)
    
    def estimate_time_remaining(self, phase: Phase) -> Optional[float]:
        """Estimate time remaining for current phase.
        
        Args:
            phase: Current phase
            
        Returns:
            Estimated seconds remaining, or None if cannot estimate
        """
        if not self.phase_start_time:
            return None
        
        elapsed = (datetime.now() - self.phase_start_time).total_seconds()
        avg_duration = self.get_average_duration(phase.value)
        
        if avg_duration <= 0:
            return None
        
        remaining = max(0, avg_duration - elapsed)
        return remaining
    
    def calculate_task_progress(self, current_phase: Phase) -> float:
        """Calculate overall task progress.
        
        Args:
            current_phase: Current phase
            
        Returns:
            Progress value between 0.0 and 1.0
        """
        phases = [Phase.STUDY, Phase.IMPLEMENT, Phase.TEST, Phase.UPDATE]
        total_phases = len(phases)
        
        # Count completed phases
        completed = 0
        for phase in phases:
            # Check if phase is in history and completed
            for entry in self.phase_history:
                if entry.get('phase') == phase.value and entry.get('success'):
                    completed += 1
                    break
        
        # Add current phase progress
        if current_phase in phases:
            phase_index = phases.index(current_phase)
            if phase_index >= completed:
                # Current phase is in progress
                phase_progress = self.calculate_phase_progress(current_phase)
                return (completed + phase_progress) / total_phases
        
        return completed / total_phases
