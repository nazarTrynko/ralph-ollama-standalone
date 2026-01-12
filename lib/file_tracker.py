#!/usr/bin/env python3
"""
File Tracker for Ralph Loop
Tracks file changes (created, modified, deleted) during loop execution.
"""

import os
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime
import json


class FileTracker:
    """Track file changes in a directory during execution."""
    
    def __init__(self, project_path: Path):
        """Initialize file tracker for a project.
        
        Args:
            project_path: Path to the project directory to track
        """
        self.project_path = Path(project_path).resolve()
        self.initial_snapshot: Set[str] = set()
        self.current_snapshot: Set[str] = set()
        self.tracked_files: Dict[str, Dict[str, any]] = {}
        
    def take_snapshot(self) -> Dict[str, str]:
        """Take a snapshot of current files in the project.
        
        Returns:
            Dictionary mapping file paths to their modification times
        """
        snapshot = {}
        
        if not self.project_path.exists():
            return snapshot
        
        for root, dirs, files in os.walk(self.project_path):
            # Skip common directories that shouldn't be tracked
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'venv', '.venv', 'node_modules', '.cursor', 'state'}]
            
            for file in files:
                file_path = Path(root) / file
                try:
                    rel_path = str(file_path.relative_to(self.project_path))
                    # Skip common files that shouldn't be tracked
                    if any(rel_path.endswith(ext) for ext in {'.pyc', '.pyo', '.pyd', '.so', '.dylib'}):
                        continue
                    if rel_path.startswith('.git/'):
                        continue
                    
                    mtime = os.path.getmtime(file_path)
                    snapshot[rel_path] = datetime.fromtimestamp(mtime).isoformat()
                except (OSError, ValueError):
                    # File might have been deleted or inaccessible
                    continue
        
        return snapshot
    
    def start_tracking(self) -> None:
        """Start tracking by taking initial snapshot."""
        self.initial_snapshot = set(self.take_snapshot().keys())
        self.current_snapshot = self.initial_snapshot.copy()
    
    def get_changes(self) -> Dict[str, List[str]]:
        """Get file changes since last snapshot.
        
        Returns:
            Dictionary with keys: 'created', 'modified', 'deleted'
        """
        current_snapshot = self.take_snapshot()
        current_files = set(current_snapshot.keys())
        
        created = current_files - self.initial_snapshot
        deleted = self.initial_snapshot - current_files
        
        # For modified files, check if they existed before and have different mtime
        modified = set()
        
        for file in current_files & self.initial_snapshot:
            # File exists in both, check if modified
            current_file = self.project_path / file
            if current_file.exists():
                try:
                    current_mtime = os.path.getmtime(current_file)
                    # If we have tracked info, compare
                    if file in self.tracked_files:
                        old_mtime = self.tracked_files[file].get('mtime')
                        if old_mtime and current_mtime > old_mtime:
                            modified.add(file)
                    else:
                        # First time tracking, check if mtime changed
                        # Compare with initial snapshot if we have it
                        initial_mtime_str = current_snapshot.get(file)
                        if initial_mtime_str:
                            try:
                                initial_mtime = datetime.fromisoformat(initial_mtime_str).timestamp()
                                if current_mtime > initial_mtime:
                                    modified.add(file)
                            except (ValueError, TypeError):
                                # Can't compare, assume not modified
                                pass
                except OSError:
                    pass
        
        return {
            'created': sorted(list(created)),
            'modified': sorted(list(modified)),
            'deleted': sorted(list(deleted))
        }
    
    def update_snapshot(self) -> Dict[str, List[str]]:
        """Update snapshot and return changes since last update.
        
        Returns:
            Dictionary with keys: 'created', 'modified', 'deleted'
        """
        changes = self.get_changes()
        
        # Update tracked files info
        current_snapshot = self.take_snapshot()
        for file in changes['created'] + changes['modified']:
            file_path = self.project_path / file
            if file_path.exists():
                try:
                    mtime = os.path.getmtime(file_path)
                    size = os.path.getsize(file_path)
                    self.tracked_files[file] = {
                        'mtime': mtime,
                        'size': size,
                        'path': str(file_path)
                    }
                except OSError:
                    pass
        
        # Update current snapshot
        self.current_snapshot = set(current_snapshot.keys())
        
        return changes
    
    def get_all_files(self) -> List[Dict[str, any]]:
        """Get all tracked files with their metadata.
        
        Returns:
            List of file dictionaries with path, status, size, mtime
        """
        files = []
        current_snapshot = self.take_snapshot()
        changes = self.get_changes()
        
        all_files = set(current_snapshot.keys()) | self.initial_snapshot
        
        for file in sorted(all_files):
            file_path = self.project_path / file
            status = 'unchanged'
            
            if file in changes['created']:
                status = 'created'
            elif file in changes['modified']:
                status = 'modified'
            elif file in changes['deleted']:
                status = 'deleted'
            
            file_info = {
                'path': file,
                'status': status,
                'exists': file_path.exists()
            }
            
            if file_path.exists():
                try:
                    file_info['size'] = os.path.getsize(file_path)
                    file_info['mtime'] = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                except OSError:
                    pass
            
            files.append(file_info)
        
        return files
