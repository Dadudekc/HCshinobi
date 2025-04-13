from typing import Dict, List, Optional
from .message_queue import Message, MessagePriority, MessageQueue
from ..agent_manager.agent_profiler import AgentProfiler

class PriorityHandler:
    def __init__(self, message_queue: MessageQueue, agent_profiler: AgentProfiler):
        self._message_queue = message_queue
        self._agent_profiler = agent_profiler
        self._priority_thresholds: Dict[MessagePriority, float] = {
            MessagePriority.CRITICAL: 0.9,
            MessagePriority.HIGH: 0.7,
            MessagePriority.MEDIUM: 0.5,
            MessagePriority.LOW: 0.3
        }
    
    def adjust_message_priority(self, message: Message) -> MessagePriority:
        # Get sender's reliability score
        reliability = self._agent_profiler.get_agent_reliability(message.sender_id)
        
        # Adjust priority based on sender reliability
        if reliability >= self._priority_thresholds[MessagePriority.CRITICAL]:
            return MessagePriority.CRITICAL
        elif reliability >= self._priority_thresholds[MessagePriority.HIGH]:
            return MessagePriority.HIGH
        elif reliability >= self._priority_thresholds[MessagePriority.MEDIUM]:
            return MessagePriority.MEDIUM
        else:
            return MessagePriority.LOW
    
    def get_priority_threshold(self, priority: MessagePriority) -> float:
        return self._priority_thresholds.get(priority, 0.0)
    
    def set_priority_threshold(self, priority: MessagePriority, threshold: float) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        self._priority_thresholds[priority] = threshold
    
    def get_messages_by_priority(self, priority: MessagePriority) -> List[Message]:
        return [
            message for message in self._message_queue._messages.values()
            if message.priority == priority
        ]
    
    def get_high_priority_messages(self, agent_id: str) -> List[Message]:
        return [
            message for message in self._message_queue.get_agent_messages(agent_id)
            if message.priority in [MessagePriority.CRITICAL, MessagePriority.HIGH]
        ]
    
    def prioritize_messages(self, messages: List[Message]) -> List[Message]:
        # Sort messages by priority and timestamp
        return sorted(
            messages,
            key=lambda x: (
                list(MessagePriority).index(x.priority),
                x.created_at
            ),
            reverse=True
        )
    
    def get_priority_distribution(self) -> Dict[MessagePriority, int]:
        distribution = {priority: 0 for priority in MessagePriority}
        for message in self._message_queue._messages.values():
            distribution[message.priority] += 1
        return distribution 