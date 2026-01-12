#!/usr/bin/env python3
"""
Response Cache for LLM responses, model selections, and file lists.
Provides smart caching with TTL and invalidation.
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any
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
            cache_dir: Directory for cache files (deprecated, kept for compatibility)
            enabled: Whether caching is enabled
            ttl_seconds: Time-to-live for cache entries in seconds
            max_size: Maximum number of cache entries (LRU eviction)
        """
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        
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
        
        # Check memory cache
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                # Move to end (most recently used)
                self.memory_cache.move_to_end(cache_key)
                logger.debug(f"Cache hit: {category}")
                return entry['value']
            else:
                # Expired, remove from memory
                del self.memory_cache[cache_key]
        
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
        logger.debug(f"Cached: {category}")
    
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
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
            logger.debug(f"Invalidated cache entry: {category}")
        elif category:
            # Invalidate all entries in category (would need category tracking)
            # For now, invalidate all if category specified
            self.memory_cache.clear()
            logger.debug(f"Invalidated cache category: {category}")
        else:
            # Invalidate all
            self.memory_cache.clear()
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
            'ttl_seconds': self.ttl_seconds
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
