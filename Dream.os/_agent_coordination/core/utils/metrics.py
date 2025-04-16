"""
Metrics and telemetry utilities for DreamOS agent coordination.
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from .base import Singleton, AsyncLockManager

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

class MetricCollector(metaclass=Singleton):
    """Collector for system metrics and telemetry data."""
    
    def __init__(self):
        self._metrics: Dict[str, List[MetricPoint]] = {}
        self._collectors: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._collection_task: Optional[asyncio.Task] = None
        self._collection_interval: float = 60.0  # Default 1 minute
        self._running = False
        
    def register_collector(self, name: str, collector: Callable) -> None:
        """Register a metric collector function."""
        self._collectors[name] = collector
        logger.info(f"Registered metric collector: {name}")
        
    def unregister_collector(self, name: str) -> None:
        """Unregister a metric collector."""
        self._collectors.pop(name, None)
        logger.info(f"Unregistered metric collector: {name}")
        
    async def record_metric(self, name: str, value: float,
                          labels: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        async with AsyncLockManager(self._lock):
            if name not in self._metrics:
                self._metrics[name] = []
                
            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                labels=labels or {}
            )
            self._metrics[name].append(point)
            
    async def get_metrics(self, name: str,
                         start_time: Optional[float] = None,
                         end_time: Optional[float] = None) -> List[MetricPoint]:
        """Get recorded metrics for a given name and time range."""
        async with AsyncLockManager(self._lock):
            if name not in self._metrics:
                return []
                
            points = self._metrics[name]
            if start_time is not None:
                points = [p for p in points if p.timestamp >= start_time]
            if end_time is not None:
                points = [p for p in points if p.timestamp <= end_time]
                
            return points
            
    def set_collection_interval(self, interval: float) -> None:
        """Set the automatic collection interval in seconds."""
        self._collection_interval = interval
        
    async def start_collection(self) -> None:
        """Start automatic metric collection."""
        if self._running:
            return
            
        self._running = True
        self._collection_task = asyncio.create_task(self._collect_metrics())
        logger.info("Started automatic metric collection")
        
    async def stop_collection(self) -> None:
        """Stop automatic metric collection."""
        if not self._running:
            return
            
        self._running = False
        if self._collection_task:
            await self._collection_task
            self._collection_task = None
        logger.info("Stopped automatic metric collection")
        
    async def _collect_metrics(self) -> None:
        """Collect metrics from registered collectors."""
        while self._running:
            try:
                for name, collector in self._collectors.items():
                    try:
                        value = collector()
                        if isinstance(value, (int, float)):
                            await self.record_metric(name, float(value))
                    except Exception as e:
                        logger.error(f"Error collecting metric {name}: {e}")
                        
                await asyncio.sleep(self._collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metric collection loop: {e}")
                await asyncio.sleep(1.0)  # Brief pause before retry

@dataclass
class TimingStats:
    """Statistics for timing measurements."""
    count: int = 0
    total_time: float = 0.0
    min_time: Optional[float] = None
    max_time: Optional[float] = None
    
    def update(self, duration: float) -> None:
        """Update statistics with a new duration."""
        self.count += 1
        self.total_time += duration
        
        if self.min_time is None or duration < self.min_time:
            self.min_time = duration
        if self.max_time is None or duration > self.max_time:
            self.max_time = duration
            
    @property
    def average_time(self) -> Optional[float]:
        """Calculate average time."""
        return self.total_time / self.count if self.count > 0 else None

class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.labels = labels or {}
        self.start_time: Optional[float] = None
        self.stats = TimingStats()
        
    async def __aenter__(self) -> 'Timer':
        self.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.stats.update(duration)
            
            # Record metric
            collector = MetricCollector()
            await collector.record_metric(
                f"timer_{self.name}",
                duration,
                self.labels
            ) 