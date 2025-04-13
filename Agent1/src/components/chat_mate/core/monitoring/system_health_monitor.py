import asyncio
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .health_metrics import HealthStatus, HealthMetrics
from .service_checker import ServiceChecker
from .resource_monitor import ResourceMonitor
from .alert_manager import AlertManager
from .metrics_storage import MetricsStorage

class SystemHealthMonitor:
    """Orchestrates system health monitoring components."""
    
    def __init__(
        self,
        service_config: Dict[str, Any],
        resource_thresholds: Dict[str, float],
        check_interval: int = 60,
        max_history: int = 1000
    ):
        self.check_interval = check_interval
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Initialize components
        self.service_checker = ServiceChecker(service_config)
        self.resource_monitor = ResourceMonitor(resource_thresholds)
        self.alert_manager = AlertManager()
        self.metrics_storage = MetricsStorage(max_history)
        
        # Setup cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    def start_monitoring(self) -> None:
        """Start the health monitoring system."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop the health monitoring system."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                asyncio.run(self._perform_checks())
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
            
            self._stop_event.wait(self.check_interval)
    
    async def _perform_checks(self) -> None:
        """Perform all health checks."""
        # Check services
        service_metrics = await self.service_checker.get_health_metrics()
        self.metrics_storage.store_metrics("services", service_metrics)
        self.alert_manager.check_health_metrics("services", service_metrics)
        
        # Check resources
        resource_metrics = self.resource_monitor.get_health_metrics()
        self.metrics_storage.store_metrics("resources", resource_metrics)
        self.alert_manager.check_health_metrics("resources", resource_metrics)
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old metrics."""
        while not self._stop_event.is_set():
            try:
                self.metrics_storage.cleanup_old_metrics(timedelta(days=7))
            except Exception as e:
                print(f"Error in cleanup task: {e}")
            
            await asyncio.sleep(3600)  # Run every hour
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        return {
            "services": self.service_checker.get_health_metrics().__dict__,
            "resources": self.resource_monitor.get_health_metrics().__dict__,
            "alerts": [
                alert.__dict__
                for alert in self.alert_manager.get_recent_alerts(limit=10)
            ]
        }
    
    def get_historical_metrics(
        self,
        component: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get historical metrics with optional filtering."""
        return self.metrics_storage.get_historical_metrics(
            component=component,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        ) 