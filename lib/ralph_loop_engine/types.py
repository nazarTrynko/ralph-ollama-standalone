#!/usr/bin/env python3
"""
Shared types for Ralph Loop Engine.
"""

from enum import Enum


class Phase(Enum):
    """Ralph workflow phases."""
    STUDY = "study"
    IMPLEMENT = "implement"
    TEST = "test"
    UPDATE = "update"
    IDLE = "idle"
    COMPLETE = "complete"
    ERROR = "error"


class LoopMode(Enum):
    """Execution mode."""
    NON_STOP = "non_stop"
    PHASE_BY_PHASE = "phase_by_phase"
