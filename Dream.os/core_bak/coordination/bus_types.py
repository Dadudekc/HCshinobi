"""Common types for the Agent Bus system."""

from enum import Enum

class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    TERMINATED = "terminated"
    SHUTDOWN_READY = "shutdown_ready" 