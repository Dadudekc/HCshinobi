"""
Main system health monitor that coordinates all component monitors.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import deque
from threading import Thread, Lock, Event

from .components.resource_monitor import ResourceMonitor
from .components.network_monitor import NetworkMonitor
from .services.mongodb_checker import MongoDBChecker
from .services.redis_checker import RedisChecker
from .utils.status_types import HealthMetrics, HealthStatus

logger = logging.getLogger(__name__)

class SystemHealthMonitor:
    """
    Centralized system health monitor with:
    - Async service checks
    - Efficient metric storage
    - Smart caching
    - Parallel health checks
    """
    
    def __init__(
        self,
        driver_manager: Any,
        memory_manager: Any,
        thread_pool: Any,
        check_interval: int = 60,
        history_size: int = 1000
    ):
        """
        Initialize the system health monitor.
        
        Args:
            driver_manager: WebDriver manager instance
            memory_manager: Memory manager instance
            thread_pool: Thread pool manager instance
            check_interval: Interval between health checks in seconds
            history_size: Number of historical metrics to keep
        """
        self.driver_manager = driver_manager
        self.memory_manager = memory_manager
        self.thread_pool = thread_pool
        self.check_interval = check_interval
        self.history_size = history_size
        
        # Initialize monitors
        self.resource_monitor = ResourceMonitor(check_interval)
        self.network_monitor = NetworkMonitor(check_interval)
        self.mongodb_checker = MongoDBChecker()
        self.redis_checker = RedisChecker()
        
        # Monitoring state
        self.component_health = {}
        self.metrics_history = deque(maxlen=history_size)
        self._lock = Lock()
        self._stop_event = Event()
        self._monitor_thread: Optional[Thread] = None
        
        # Event loop for async operations
        self.loop = asyncio.new_event_loop()
        
    def start_monitoring(self) -> None:
        """Start the health monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Health monitoring is already running")
            return
            
        self._stop_event.clear()
        self._monitor_thread = Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="SystemHealthMonitor"
        )
        self._monitor_thread.start()
        logger.info("System health monitoring started")
        
    def stop_monitoring(self) -> None:
        """Stop the health monitoring thread."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("System health monitoring stopped")
        
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                # Run health checks
                asyncio.run_coroutine_threadsafe(
                    self.perform_health_checks(),
                    self.loop
                )
                
                # Store metrics
                self._store_metrics()
                
                # Check for alerts
                self._check_alerts()
                
                # Wait for next check interval
                self._stop_event.wait(timeout=self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self._stop_event.wait(timeout=5.0)  # Brief pause on error
                
    async def perform_health_checks(self) -> Dict[str, HealthMetrics]:
        """
        Perform health checks on all system components.
        
        Returns:
            Dictionary of component health metrics
        """
        with self._lock:
            # Run all checks in parallel
            results = await asyncio.gather(
                self.resource_monitor.check_health(),
                self.network_monitor.check_health(),
                self.mongodb_checker.check_health(),
                self.redis_checker.check_health(),
                return_exceptions=True
            )
            
            # Process results
            self.component_health = {
                "system": self._handle_check_result(results[0], "System Resources"),
                "network": self._handle_check_result(results[1], "Network"),
                "mongodb": self._handle_check_result(results[2], "MongoDB"),
                "redis": self._handle_check_result(results[3], "Redis")
            }
            
            return self.component_health
            
    def _handle_check_result(
        self,
        result: Any,
        component_name: str
    ) -> HealthMetrics:
        """Handle a health check result, converting exceptions to error metrics."""
        if isinstance(result, Exception):
            return HealthMetrics.create_error(
                f"{component_name} check failed",
                result
            )
        return result
        
    def _store_metrics(self) -> None:
        """Store current metrics in history."""
        try:
            metrics_entry = {
                "timestamp": datetime.now().isoformat(),
                "components": {}
            }
            
            with self._lock:
                for component, health_metrics in self.component_health.items():
                    metrics_entry["components"][component] = health_metrics.to_dict()
                    
                self.metrics_history.append(metrics_entry)
                
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
            
    def _check_alerts(self) -> None:
        """Check for alert conditions and log them."""
        try:
            unhealthy_components = [
                name for name, health in self.component_health.items()
                if health.status == HealthStatus.UNHEALTHY
            ]
            
            degraded_components = [
                name for name, health in self.component_health.items()
                if health.status == HealthStatus.DEGRADED
            ]
            
            if unhealthy_components:
                logger.error(
                    f"Unhealthy components detected: {', '.join(unhealthy_components)}"
                )
                
            if degraded_components:
                logger.warning(
                    f"Degraded components detected: {', '.join(degraded_components)}"
                )
                
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get current system health status.
        
        Returns:
            Dictionary containing overall system health metrics
        """
        with self._lock:
            component_status = {
                name: health.to_dict()
                for name, health in self.component_health.items()
            }
            
            # Calculate overall status
            status_values = [h.status for h in self.component_health.values()]
            if any(s == HealthStatus.UNHEALTHY for s in status_values):
                overall_status = HealthStatus.UNHEALTHY
            elif any(s == HealthStatus.DEGRADED for s in status_values):
                overall_status = HealthStatus.DEGRADED
            else:
                overall_status = HealthStatus.HEALTHY
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": overall_status.name,
                "components": component_status,
                "active_monitoring": bool(self._monitor_thread and self._monitor_thread.is_alive())
            }
            
    def get_historical_metrics(
        self,
        component: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics for analysis.
        
        Args:
            component: Optional component name to filter metrics
            start_time: Optional start time for metrics
            end_time: Optional end time for metrics
            
        Returns:
            List of historical metrics matching the filters
        """
        with self._lock:
            filtered_metrics = list(self.metrics_history)
            
        if start_time:
            filtered_metrics = [
                m for m in filtered_metrics
                if datetime.fromisoformat(m["timestamp"]) >= start_time
            ]
            
        if end_time:
            filtered_metrics = [
                m for m in filtered_metrics
                if datetime.fromisoformat(m["timestamp"]) <= end_time
            ]
            
        if component:
            filtered_metrics = [
                {
                    "timestamp": m["timestamp"],
                    "components": {component: m["components"][component]}
                }
                for m in filtered_metrics
                if component in m["components"]
            ]
            
        return filtered_metrics
        
    def get_component_metrics(self, component: str) -> Optional[HealthMetrics]:
        """Get current metrics for a specific component."""
        return self.component_health.get(component)
        
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage metrics."""
        return self.resource_monitor.get_resource_usage()
        
    def get_network_stats(self) -> Dict[str, Any]:
        """Get current network statistics."""
        return self.network_monitor.get_network_stats()
        
    def get_mongodb_info(self) -> Dict[str, Any]:
        """Get MongoDB connection information."""
        return self.mongodb_checker.get_connection_info()
        
    def get_redis_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        return self.redis_checker.get_cache_stats() 