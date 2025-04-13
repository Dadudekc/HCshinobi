import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import psutil
import time
import threading
from dataclasses import dataclass

from .alert_handlers import AlertHandler

@dataclass
class MetricValue:
    """Represents a single metric measurement with metadata."""
    value: float
    timestamp: datetime
    metadata: Dict[str, Any]
    alert_sent: bool = False
    last_alert_time: Optional[datetime] = None

class MetricsMonitor:
    """Monitors and manages database metrics with alerting capabilities."""
    
    def __init__(self, config_path: str = "config/project/alert_config.json"):
        """Initialize the metrics monitor with configuration."""
        self.logger = logging.getLogger(__name__)
        self.metrics: Dict[str, List[MetricValue]] = {}
        self.alert_handler = AlertHandler(config_path)
        self._load_config(config_path)
        
        self._lock = threading.Lock()
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_old_metrics, daemon=True)
        self._monitor_thread = threading.Thread(target=self._monitor_system_metrics, daemon=True)
        self._cleanup_thread.start()
        self._monitor_thread.start()

    def _load_config(self, config_path: str) -> None:
        """Load monitoring configuration from file."""
        try:
            with open(config_path) as f:
                config = json.load(f)
            self.thresholds = config.get('alert_thresholds', {})
            self.retention_days = config.get('retention_days', 30)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise

    def record_metric(self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a new metric value with optional metadata."""
        with self._lock:
            metric = MetricValue(
                value=value,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(metric)
            
            self._check_thresholds(name, metric)

    def _check_thresholds(self, name: str, metric: MetricValue) -> None:
        """Check if metric value exceeds thresholds and trigger alerts."""
        if name not in self.thresholds:
            return

        threshold = self.thresholds[name]
        delay = threshold.get('delay', 300)  # Default 5 minutes between alerts

        if metric.value >= threshold.get('critical', float('inf')):
            self._send_alert(name, metric, 'CRITICAL', delay)
        elif metric.value >= threshold.get('warning', float('inf')):
            self._send_alert(name, metric, 'WARNING', delay)

    def _send_alert(self, name: str, metric: MetricValue, level: str, delay: int) -> None:
        """Send an alert if conditions are met."""
        if (metric.last_alert_time and 
            datetime.now() - metric.last_alert_time < timedelta(seconds=delay)):
            return

        message = (
            f"{level} Alert: Metric '{name}' value {metric.value} "
            f"exceeded {level.lower()} threshold\n"
            f"Timestamp: {metric.timestamp}\n"
            f"Metadata: {metric.metadata}"
        )

        try:
            self.alert_handler(message, level)
            metric.alert_sent = True
            metric.last_alert_time = datetime.now()
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")

    def get_metric_values(self, name: str, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> List[MetricValue]:
        """Retrieve metric values within the specified time range."""
        with self._lock:
            if name not in self.metrics:
                return []
            
            values = self.metrics[name]
            if start_time:
                values = [v for v in values if v.timestamp >= start_time]
            if end_time:
                values = [v for v in values if v.timestamp <= end_time]
            
            return values

    def get_current_value(self, name: str) -> Optional[float]:
        """Get the most recent value for a metric."""
        with self._lock:
            if name not in self.metrics or not self.metrics[name]:
                return None
            return self.metrics[name][-1].value

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about all monitored metrics."""
        with self._lock:
            stats = {}
            for name, values in self.metrics.items():
                if not values:
                    continue
                    
                current = values[-1].value
                avg = sum(v.value for v in values) / len(values)
                max_val = max(v.value for v in values)
                min_val = min(v.value for v in values)
                
                stats[name] = {
                    'current': current,
                    'average': avg,
                    'maximum': max_val,
                    'minimum': min_val,
                    'num_measurements': len(values),
                    'last_updated': values[-1].timestamp.isoformat()
                }
            return stats

    def _cleanup_old_metrics(self) -> None:
        """Periodically remove metrics older than retention period."""
        while self._running:
            try:
                cutoff = datetime.now() - timedelta(days=self.retention_days)
                with self._lock:
                    for name in list(self.metrics.keys()):
                        self.metrics[name] = [
                            m for m in self.metrics[name]
                            if m.timestamp >= cutoff
                        ]
                time.sleep(3600)  # Clean up every hour
            except Exception as e:
                self.logger.error(f"Error in cleanup thread: {e}")
                time.sleep(60)  # Wait before retrying

    def _monitor_system_metrics(self) -> None:
        """Monitor system metrics in background."""
        while self._running:
            try:
                # Monitor CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric('system.cpu_usage', cpu_percent)

                # Monitor memory usage
                memory = psutil.virtual_memory()
                self.record_metric('system.memory_usage', memory.percent)

                # Monitor disk usage
                disk = psutil.disk_usage('/')
                self.record_metric('system.disk_usage', disk.percent)

                time.sleep(60)  # Monitor every minute
            except Exception as e:
                self.logger.error(f"Error in monitoring thread: {e}")
                time.sleep(60)  # Wait before retrying

    def generate_report(self, start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate a comprehensive monitoring report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'period': {
                'start': start_time.isoformat() if start_time else None,
                'end': end_time.isoformat() if end_time else None
            },
            'metrics': {}
        }

        metric_names = metrics if metrics else list(self.metrics.keys())
        for name in metric_names:
            values = self.get_metric_values(name, start_time, end_time)
            if not values:
                continue

            report['metrics'][name] = {
                'current_value': values[-1].value,
                'average': sum(v.value for v in values) / len(values),
                'min': min(v.value for v in values),
                'max': max(v.value for v in values),
                'num_measurements': len(values),
                'num_alerts': sum(1 for v in values if v.alert_sent),
                'thresholds': self.thresholds.get(name, {}),
                'last_alert': max(
                    (v.last_alert_time for v in values if v.last_alert_time),
                    default=None
                )
            }

        return report

    def shutdown(self) -> None:
        """Gracefully shut down the monitoring system."""
        self._running = False
        self._cleanup_thread.join(timeout=5)
        self._monitor_thread.join(timeout=5)
        self.logger.info("Metrics monitor shutdown complete") 