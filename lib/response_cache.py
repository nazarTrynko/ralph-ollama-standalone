#!/usr/bin/env python3
"""
Response Cache for LLM responses, model selections, and file lists.
Provides smart caching with TTL and invalidation.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import OrderedDict
from lib.logging_config import get_logger

logger = get_logger('response_cache')


class ResponseCache:
    """Cache for LLM responses, model selections, and file lists."""
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        enabled: bool = True,
        ttl_seconds: int = 3600,
        max_size: int = 100
    ):
        """Initialize response cache.
        
        Args:
            cache_dir: Directory for cache files (default: state/cache)
            enabled: Whether caching is enabled
            ttl_seconds: Time-to-live for cache entries in seconds
            max_size: Maximum number of cache entries (LRU eviction)
        """
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to state/cache in project root
            project_root = Path(__file__).parent.parent
            self.cache_dir = project_root / 'state' / 'cache'
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory LRU cache for fast access
        self.memory_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        logger.info(f"ResponseCache initialized: enabled={enabled}, ttl={ttl_seconds}s, max_size={max_size}")
    
    def _get_cache_key(self, category: str, key_data: Any) -> str:
        """Generate cache key from category and key data.
        
        Args:
            category: Cache category (e.g., 'llm_response', 'model_list', 'file_list')
            key_data: Data to generate key from (dict, str, etc.)
        
        Returns:
            Cache key string
        """
        if isinstance(key_data, dict):
            # Sort keys for consistent hashing
            key_str = json.dumps(key_data, sort_keys=True)
        else:
            key_str = str(key_data)
        
        full_key = f"{category}:{key_str}"
        return hashlib.md5(full_key.encode()).hexdigest()
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Get cache file path for a key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, category: str, key_data: Any) -> Optional[Any]:
        """Get cached value.
        
        Args:
            category: Cache category
            key_data: Key data
        
        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None
        
        cache_key = self._get_cache_key(category, key_data)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                # Move to end (most recently used)
                self.memory_cache.move_to_end(cache_key)
                logger.debug(f"Cache hit (memory): {category}")
                return entry['value']
            else:
                # Expired, remove from memory
                del self.memory_cache[cache_key]
        
        # Check disk cache
        cache_file = self._get_cache_file(cache_key)
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    entry = json.load(f)
                
                # Check TTL
                if time.time() - entry['timestamp'] < self.ttl_seconds:
                    # Load into memory cache
                    self._add_to_memory_cache(cache_key, entry['value'], entry['timestamp'])
                    logger.debug(f"Cache hit (disk): {category}")
                    return entry['value']
                else:
                    # Expired, delete file
                    cache_file.unlink()
                    logger.debug(f"Cache expired: {category}")
            except (json.JSONDecodeError, IOError, KeyError) as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")
                # Delete corrupted cache file
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        
        logger.debug(f"Cache miss: {category}")
        return None
    
    def set(self, category: str, key_data: Any, value: Any) -> None:
        """Set cached value.
        
        Args:
            category: Cache category
            key_data: Key data
            value: Value to cache
        """
        if not self.enabled:
            return
        
        cache_key = self._get_cache_key(category, key_data)
        timestamp = time.time()
        
        # Add to memory cache
        self._add_to_memory_cache(cache_key, value, timestamp)
        
        # Save to disk
        cache_file = self._get_cache_file(cache_key)
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'value': value,
                    'timestamp': timestamp,
                    'category': category
                }, f)
            logger.debug(f"Cached: {category}")
        except IOError as e:
            logger.warning(f"Error writing cache file {cache_file}: {e}")
    
    def _add_to_memory_cache(self, cache_key: str, value: Any, timestamp: float) -> None:
        """Add entry to memory cache with LRU eviction."""
        # Remove if exists (will be re-added at end)
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        
        # Add to end
        self.memory_cache[cache_key] = {
            'value': value,
            'timestamp': timestamp
        }
        
        # Evict oldest if over limit
        while len(self.memory_cache) > self.max_size:
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
    
    def invalidate(self, category: Optional[str] = None, key_data: Optional[Any] = None) -> None:
        """Invalidate cache entries.
        
        Args:
            category: Category to invalidate (None = all categories)
            key_data: Specific key to invalidate (None = all in category)
        """
        if category and key_data:
            # Invalidate specific entry
            cache_key = self._get_cache_key(category, key_data)
            
            # Remove from memory
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
            
            # Remove from disk
            cache_file = self._get_cache_file(cache_key)
            if cache_file.exists():
                cache_file.unlink()
            
            logger.debug(f"Invalidated cache entry: {category}")
        elif category:
            # Invalidate all entries in category
            keys_to_remove = []
            for key in list(self.memory_cache.keys()):
                # Check disk files for category
                cache_file = self._get_cache_file(key)
                if cache_file.exists():
                    try:
                        with open(cache_file, 'r') as f:
                            entry = json.load(f)
                        if entry.get('category') == category:
                            keys_to_remove.append(key)
                            cache_file.unlink()
                    except (json.JSONDecodeError, IOError, KeyError):
                        pass
            
            # Remove from memory
            for key in keys_to_remove:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            
            logger.debug(f"Invalidated cache category: {category}")
        else:
            # Invalidate all
            self.memory_cache.clear()
            
            # Remove all cache files
            for cache_file in self.cache_dir.glob('*.json'):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
            
            logger.info("Invalidated all cache entries")
    
    def clear_expired(self) -> int:
        """Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        if not self.enabled:
            return 0
        
        cleared = 0
        current_time = time.time()
        
        # Clear from memory
        keys_to_remove = []
        for key, entry in self.memory_cache.items():
            if current_time - entry['timestamp'] >= self.ttl_seconds:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.memory_cache[key]
            cleared += 1
        
        # Clear from disk
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r') as f:
                    entry = json.load(f)
                
                if current_time - entry.get('timestamp', 0) >= self.ttl_seconds:
                    cache_file.unlink()
                    cleared += 1
            except (json.JSONDecodeError, IOError, KeyError):
                # Corrupted file, delete it
                try:
                    cache_file.unlink()
                    cleared += 1
                except OSError:
                    pass
        
        if cleared > 0:
            logger.debug(f"Cleared {cleared} expired cache entries")
        
        return cleared
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            'enabled': self.enabled,
            'memory_entries': len(self.memory_cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds,
            'cache_dir': str(self.cache_dir)
        }


# Global cache instance
_global_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get global cache instance."""
    global _global_cache
    
    if _global_cache is None:
        # Load config to get cache settings
        try:
            from lib.config import load_and_validate_config, DEFAULT_CONFIG_PATH
            # Convert string path to Path object before passing to load_and_validate_config
            config_path = Path(DEFAULT_CONFIG_PATH)
            config = load_and_validate_config(config_path)
            cache_config = config.get('cache', {})
            
            _global_cache = ResponseCache(
                enabled=cache_config.get('enabled', True),
                ttl_seconds=cache_config.get('ttlSeconds', 3600),
                max_size=cache_config.get('maxSize', 100)
            )
        except Exception as e:
            logger.warning(f"Error loading cache config, using defaults: {e}")
            _global_cache = ResponseCache()
    
    return _global_cache
