"""
Optional performance metrics tracking for Ralph Ollama integration.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
from collections import defaultdict


class MetricsCollector:
    """Collects and tracks performance metrics."""
    
    def __init__(self, enabled: bool = True, log_path: Optional[Path] = None):
        """
        Initialize metrics collector.
        
        Args:
            enabled: Whether metrics collection is enabled
            log_path: Optional path to save metrics
        """
        self.enabled = enabled
        self.log_path = log_path
        self.metrics: List[Dict[str, Any]] = []
        self._stats = defaultdict(lambda: {'count': 0, 'total_tokens': 0, 'total_time': 0.0})
    
    def record_request(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration: float,
        success: bool = True
    ) -> None:
        """
        Record a request metric.
        
        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            duration: Request duration in seconds
            success: Whether request was successful
        """
        if not self.enabled:
            return
        
        metric = {
            'timestamp': datetime.now().isoformat(),
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
            'duration': duration,
            'success': success,
        }
        
        self.metrics.append(metric)
        
        # Update stats
        key = f"{model}"
        self._stats[key]['count'] += 1
        self._stats[key]['total_tokens'] += prompt_tokens + completion_tokens
        self._stats[key]['total_time'] += duration
        
        # Save if log_path is set
        if self.log_path:
            self._save_metrics()
    
    def get_stats(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a model or all models.
        
        Args:
            model: Optional model name to filter by
            
        Returns:
            Dictionary with statistics
        """
        if model:
            stats = self._stats.get(model, {})
            if stats['count'] > 0:
                return {
                    'model': model,
                    'count': stats['count'],
                    'total_tokens': stats['total_tokens'],
                    'total_time': stats['total_time'],
                    'avg_tokens': stats['total_tokens'] / stats['count'],
                    'avg_time': stats['total_time'] / stats['count'],
                    'tokens_per_second': stats['total_tokens'] / stats['total_time'] if stats['total_time'] > 0 else 0,
                }
            return {}
        
        # Return stats for all models
        result = {}
        for model_name, stats in self._stats.items():
            if stats['count'] > 0:
                result[model_name] = {
                    'count': stats['count'],
                    'total_tokens': stats['total_tokens'],
                    'total_time': stats['total_time'],
                    'avg_tokens': stats['total_tokens'] / stats['count'],
                    'avg_time': stats['total_time'] / stats['count'],
                    'tokens_per_second': stats['total_tokens'] / stats['total_time'] if stats['total_time'] > 0 else 0,
                }
        return result
    
    def get_recent_metrics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent metrics.
        
        Args:
            limit: Number of recent metrics to return
            
        Returns:
            List of recent metrics
        """
        return self.metrics[-limit:]
    
    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self._stats.clear()
    
    def _save_metrics(self) -> None:
        """Save metrics to file."""
        if not self.log_path:
            return
        
        log_path = Path(self.log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'metrics': self.metrics[-100:],  # Keep last 100
            'stats': dict(self._stats),
            'last_updated': datetime.now().isoformat(),
        }
        
        with open(log_path, 'w') as f:
            json.dump(data, f, indent=2)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(enabled: bool = True, log_path: Optional[Path] = None) -> MetricsCollector:
    """
    Get or create global metrics collector.
    
    Args:
        enabled: Whether metrics collection is enabled
        log_path: Optional path to save metrics
        
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(enabled=enabled, log_path=log_path)
    return _metrics_collector


def record_request(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration: float,
    success: bool = True
) -> None:
    """
    Record a request metric (convenience function).
    
    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        duration: Request duration in seconds
        success: Whether request was successful
    """
    collector = get_metrics_collector()
    collector.record_request(model, prompt_tokens, completion_tokens, duration, success)
