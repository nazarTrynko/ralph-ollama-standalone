#!/usr/bin/env python3
"""
File Tracker for Ralph Loop
Tracks file changes (created, modified, deleted) during loop execution.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
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
        
        # Optimization: Cache snapshots and metadata
        self._snapshot_cache: Optional[Dict[str, str]] = None
        self._snapshot_cache_time: Optional[float] = 0.0
        self._cache_ttl: float = 0.5  # Cache for 500ms
        self._last_check_time: float = 0.0
        self._check_interval: float = 0.2  # Minimum interval between checks (200ms)
        
    def take_snapshot(self, force_refresh: bool = False) -> Dict[str, str]:
        """Take a snapshot of current files in the project.
        
        Args:
            force_refresh: If True, bypass cache and take fresh snapshot
            
        Returns:
            Dictionary mapping file paths to their modification times
        """
        current_time = time.time()
        
        # Use cached snapshot if available and fresh
        if not force_refresh and self._snapshot_cache is not None:
            cache_age = current_time - self._snapshot_cache_time
            if cache_age < self._cache_ttl:
                return self._snapshot_cache.copy()
        
        snapshot = {}
        
        if not self.project_path.exists():
            self._snapshot_cache = snapshot
            self._snapshot_cache_time = current_time
            return snapshot
        
        # Batch file operations
        exclude_dirs = {'.git', '__pycache__', 'venv', '.venv', 'node_modules', '.cursor', 'state'}
        exclude_exts = {'.pyc', '.pyo', '.pyd', '.so', '.dylib'}
        
        # Collect all file paths first
        file_paths = []
        for root, dirs, files in os.walk(self.project_path):
            # Modify dirs in-place to prune excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = Path(root) / file
                try:
                    rel_path = str(file_path.relative_to(self.project_path))
                    # Skip excluded files
                    if any(rel_path.endswith(ext) for ext in exclude_exts):
                        continue
                    if rel_path.startswith('.git/'):
                        continue
                    file_paths.append((rel_path, file_path))
                except (OSError, ValueError):
                    continue
        
        # Batch stat operations
        for rel_path, file_path in file_paths:
            try:
                mtime = os.path.getmtime(file_path)
                snapshot[rel_path] = datetime.fromtimestamp(mtime).isoformat()
            except (OSError, ValueError):
                continue
        
        # Update cache
        self._snapshot_cache = snapshot
        self._snapshot_cache_time = current_time
        
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
        current_time = time.time()
        
        # Throttle checks to avoid excessive file system operations
        if current_time - self._last_check_time < self._check_interval:
            # Return cached changes if available
            if hasattr(self, '_last_changes'):
                return self._last_changes
        
        current_snapshot = self.take_snapshot()
        current_files = set(current_snapshot.keys())
        
        created = current_files - self.initial_snapshot
        deleted = self.initial_snapshot - current_files
        
        # For modified files, use cached metadata to avoid redundant stat calls
        modified = set()
        common_files = current_files & self.initial_snapshot
        
        # Batch check modifications using cached metadata
        for file in common_files:
            # Use cached tracked info if available
            if file in self.tracked_files:
                tracked_info = self.tracked_files[file]
                old_mtime = tracked_info.get('mtime')
                
                # Get current mtime from snapshot (already cached)
                current_mtime_str = current_snapshot.get(file)
                if current_mtime_str and old_mtime:
                    try:
                        current_mtime = datetime.fromisoformat(current_mtime_str).timestamp()
                        if current_mtime > old_mtime:
                            modified.add(file)
                    except (ValueError, TypeError):
                        pass
            else:
                # First time tracking - check if file was modified since initial snapshot
                # This is less common, so we can do a direct check
                current_file = self.project_path / file
                if current_file.exists():
                    try:
                        current_mtime = os.path.getmtime(current_file)
                        initial_mtime_str = current_snapshot.get(file)
                        if initial_mtime_str:
                            try:
                                initial_mtime = datetime.fromisoformat(initial_mtime_str).timestamp()
                                if current_mtime > initial_mtime:
                                    modified.add(file)
                            except (ValueError, TypeError):
                                pass
                    except OSError:
                        pass
        
        changes = {
            'created': sorted(list(created)),
            'modified': sorted(list(modified)),
            'deleted': sorted(list(deleted))
        }
        
        # Cache changes
        self._last_changes = changes
        self._last_check_time = current_time
        
        return changes
    
    def update_snapshot(self) -> Dict[str, List[str]]:
        """Update snapshot and return changes since last update.
        
        Returns:
            Dictionary with keys: 'created', 'modified', 'deleted'
        """
        changes = self.get_changes()
        
        # Batch update tracked files info
        if changes['created'] or changes['modified']:
            current_snapshot = self.take_snapshot()  # Use cached snapshot
            
            # Batch stat operations for changed files
            files_to_update = changes['created'] + changes['modified']
            for file in files_to_update:
                file_path = self.project_path / file
                if file_path.exists():
                    try:
                        # Single stat call for both mtime and size
                        stat_info = file_path.stat()
                        self.tracked_files[file] = {
                            'mtime': stat_info.st_mtime,
                            'size': stat_info.st_size,
                            'path': str(file_path)
                        }
                    except OSError:
                        pass
        
        # Update current snapshot (use cached snapshot if available)
        if 'current_snapshot' not in locals():
            current_snapshot = self.take_snapshot()
        self.current_snapshot = set(current_snapshot.keys())
        
        # Invalidate cache to force refresh on next call
        self._snapshot_cache = None
        
        return changes
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all tracked files with their metadata.
        
        Returns:
            List of file dictionaries with path, status, size, mtime
        """
        # Use cached snapshot and changes
        current_snapshot = self.take_snapshot()
        changes = self.get_changes()
        
        all_files = set(current_snapshot.keys()) | self.initial_snapshot
        files = []
        
        # Batch file info collection
        for file in sorted(all_files):
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
                'exists': file in current_snapshot
            }
            
            # Use cached tracked info if available
            if file in self.tracked_files:
                tracked_info = self.tracked_files[file]
                file_info['size'] = tracked_info.get('size')
                if tracked_info.get('mtime'):
                    file_info['mtime'] = datetime.fromtimestamp(tracked_info['mtime']).isoformat()
            elif file in current_snapshot:
                # Fallback to direct stat if not in cache
                file_path = self.project_path / file
                if file_path.exists():
                    try:
                        stat_info = file_path.stat()
                        file_info['size'] = stat_info.st_size
                        file_info['mtime'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    except OSError:
                        pass
            
            files.append(file_info)
        
        return files
