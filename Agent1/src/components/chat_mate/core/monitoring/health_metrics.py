from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, Optional

class HealthStatus(Enum):
    """System component health status."""
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()

@dataclass
class HealthMetrics:
    """Health metrics for a system component."""
    status: HealthStatus
    message: str
    metrics: Dict[str, Any]
    last_check: datetime

class IHealthMetricsProvider:
    """Interface for components that provide health metrics."""
    
    def get_health_metrics(self) -> HealthMetrics:
        """Get current health metrics for the component."""
        raise NotImplementedError()
    
    def get_historical_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get historical health metrics for the component."""
        raise NotImplementedError() 