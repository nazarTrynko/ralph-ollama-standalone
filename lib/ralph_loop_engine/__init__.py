"""
Ralph Loop Engine Package
Modular components for executing Ralph workflow loops.
"""

from lib.ralph_loop_engine.types import Phase, LoopMode

# Import RalphLoopEngine from the main engine file
# Note: The main engine is still in lib/ralph_loop_engine.py (not yet moved to this package)
# This creates a temporary import path until full refactoring is complete
import importlib.util
from pathlib import Path

_engine_path = Path(__file__).parent.parent / 'ralph_loop_engine.py'
_spec = importlib.util.spec_from_file_location("_ralph_loop_engine_module", _engine_path)
_engine_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_engine_module)
RalphLoopEngine = _engine_module.RalphLoopEngine

__all__ = ['RalphLoopEngine', 'Phase', 'LoopMode']
