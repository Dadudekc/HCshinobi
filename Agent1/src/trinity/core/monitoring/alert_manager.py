from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertStatus(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class Alert(BaseModel):
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    source: str
    created_at: datetime = datetime.now()
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

class AlertManager:
    def __init__(self):
        self._alerts: Dict[str, Alert] = {}
        self._alert_rules: Dict[str, Dict[str, Any]] = {}
    
    def create_alert(self, title: str, description: str, severity: AlertSeverity,
                    source: str, metadata: Dict[str, Any] = None) -> Alert:
        alert_id = f"alert_{len(self._alerts)}"
        
        alert = Alert(
            alert_id=alert_id,
            title=title,
            description=description,
            severity=severity,
            source=source,
            metadata=metadata or {}
        )
        
        self._alerts[alert_id] = alert
        return alert
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        return self._alerts.get(alert_id)
    
    def get_alerts_by_status(self, status: AlertStatus) -> List[Alert]:
        return [
            alert for alert in self._alerts.values()
            if alert.status == status
        ]
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        return [
            alert for alert in self._alerts.values()
            if alert.severity == severity
        ]
    
    def acknowledge_alert(self, alert_id: str) -> None:
        if alert_id not in self._alerts:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert = self._alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now()
    
    def resolve_alert(self, alert_id: str) -> None:
        if alert_id not in self._alerts:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert = self._alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
    
    def add_alert_rule(self, rule_id: str, condition: Dict[str, Any]) -> None:
        self._alert_rules[rule_id] = condition
    
    def remove_alert_rule(self, rule_id: str) -> None:
        if rule_id in self._alert_rules:
            del self._alert_rules[rule_id]
    
    def evaluate_alert_rules(self, metrics: Dict[str, float]) -> List[Alert]:
        new_alerts = []
        
        for rule_id, condition in self._alert_rules.items():
            if self._evaluate_condition(metrics, condition):
                alert = self.create_alert(
                    title=f"Rule {rule_id} triggered",
                    description=f"Condition {condition} was met",
                    severity=AlertSeverity.WARNING,
                    source="alert_rule",
                    metadata={"rule_id": rule_id, "condition": condition}
                )
                new_alerts.append(alert)
        
        return new_alerts
    
    def _evaluate_condition(self, metrics: Dict[str, float], condition: Dict[str, Any]) -> bool:
        # Simple condition evaluation
        # In a real implementation, this would be more sophisticated
        for metric, threshold in condition.items():
            if metric in metrics and metrics[metric] > threshold:
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        return self.get_alerts_by_status(AlertStatus.ACTIVE)
    
    def get_alert_summary(self) -> Dict[AlertSeverity, int]:
        summary = {severity: 0 for severity in AlertSeverity}
        for alert in self._alerts.values():
            if alert.status == AlertStatus.ACTIVE:
                summary[alert.severity] += 1
 