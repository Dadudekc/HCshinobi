"""
Core Monitoring Module
Handles system monitoring, metrics collection, and health checks.
"""

from typing import Dict, Any, Optional
from datetime import datetime

class SystemMonitor:
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.health_checks: Dict[str, Any] = {}
        
    def record_metric(self, name: str, value: Any, timestamp: Optional[datetime] = None):
        """Record a metric value."""
        if name not in self.metrics:
            self.metrics[name] = []
            
        self.metrics[name].append({
            'value': value,
            'timestamp': timestamp or datetime.utcnow()
        })
        
    def get_metrics(self, name: str) -> list:
        """Get recorded metrics for a given name."""
        return self.metrics.get(name, [])
        
    def register_health_check(self, name: str, check_func: callable):
        """Register a new health check function."""
        self.health_checks[name] = check_func
        
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        for name, check_func in self.health_checks.items():
            try:
                results[name] = {
                    'status': 'healthy',
                    'result': check_func()
                }
            except Exception as e:
                results[name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        return results 