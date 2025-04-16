from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class ErrorDetail:
    code: str
    message: str

@dataclass
class MetricsData:
    duration: float
    memory_used: str
    tokens_used: int

@dataclass
class FeedbackEventMessage:
    type: str = "FEEDBACK_EVENT"
    origin: str
    task_id: str
    agent_id: str
    status: str  # 'success' | 'failed' | 'partial'
    retry_allowed: bool
    requires_prompt_update: bool
    retry_priority: str
    output: str
    errors: List[ErrorDetail]
    metrics: MetricsData
    timestamp: str = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "origin": self.origin,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "retry_allowed": self.retry_allowed,
            "requires_prompt_update": self.requires_prompt_update,
            "retry_priority": self.retry_priority,
            "output": self.output,
            "errors": [{"code": e.code, "message": e.message} for e in self.errors],
            "metrics": {
                "duration": self.metrics.duration,
                "memory_used": self.metrics.memory_used,
                "tokens_used": self.metrics.tokens_used
            },
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FeedbackEventMessage':
        errors = [ErrorDetail(**e) for e in data.get("errors", [])]
        metrics = MetricsData(**data.get("metrics", {}))
        return cls(
            origin=data["origin"],
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            status=data["status"],
            retry_allowed=data["retry_allowed"],
            requires_prompt_update=data["requires_prompt_update"],
            retry_priority=data["retry_priority"],
            output=data["output"],
            errors=errors,
            metrics=metrics,
            timestamp=data.get("timestamp")
        ) 