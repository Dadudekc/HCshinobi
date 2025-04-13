from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime, timedelta

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"

class HealthCheck(BaseModel):
    agent_id: str
    status: HealthStatus
    last_heartbeat: datetime
    metrics: Dict[str, float]
    errors: List[str] = []

class HealthMonitor:
    def __init__(self, heartbeat_timeout: int = 300):  # 5 minutes default
        self._health_checks: Dict[str, HealthCheck] = {}
        self._heartbeat_timeout = heartbeat_timeout
        self._error_thresholds: Dict[str, float] = {
            "cpu_usage": 90.0,
            "memory_usage": 85.0,
            "response_time": 1000.0  # milliseconds
        }
    
    def update_health_check(self, agent_id: str, metrics: Dict[str, float], 
                          errors: List[str] = None) -> HealthCheck:
        current_time = datetime.now()
        
        # Calculate health status
        status = self._calculate_health_status(metrics, errors or [])
        
        health_check = HealthCheck(
            agent_id=agent_id,
            status=status,
            last_heartbeat=current_time,
            metrics=metrics,
            errors=errors or []
        )
        
        self._health_checks[agent_id] = health_check
        return health_check
    
    def _calculate_health_status(self, metrics: Dict[str, float], errors: List[str]) -> HealthStatus:
        if errors:
            return HealthStatus.CRITICAL
        
        for metric, threshold in self._error_thresholds.items():
            if metric in metrics and metrics[metric] > threshold:
                return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    def get_health_check(self, agent_id: str) -> Optional[HealthCheck]:
        return self._health_checks.get(agent_id)
    
    def get_all_health_checks(self) -> List[HealthCheck]:
        return list(self._health_checks.values())
    
    def check_agent_health(self, agent_id: str) -> HealthStatus:
        health_check = self.get_health_check(agent_id)
        if not health_check:
            return HealthStatus.OFFLINE
        
        # Check if agent is offline (no heartbeat within timeout)
        time_since_heartbeat = datetime.now() - health_check.last_heartbeat
        if time_since_heartbeat > timedelta(seconds=self._heartbeat_timeout):
            return HealthStatus.OFFLINE
        
        return health_check.status
    
    def get_unhealthy_agents(self) -> List[str]:
        unhealthy_agents = []
        for agent_id, health_check in self._health_checks.items():
            if health_check.status != HealthStatus.HEALTHY:
                unhealthy_agents.append(agent_id)
        return unhealthy_agents
    
    def set_error_threshold(self, metric: str, threshold: float) -> None:
        self._error_thresholds[metric] = threshold
    
    def get_error_threshold(self, metric: str) -> Optional[float]:
        return self._error_thresholds.get(metric)
    
    def get_health_summary(self) -> Dict[HealthStatus, int]:
        summary = {status: 0 for status in HealthStatus}
        for health_check in self._health_checks.values():
            summary[health_check.status] += 1
        return summary 