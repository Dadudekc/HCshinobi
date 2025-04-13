from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class MessagePriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MessageStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    PROCESSED = "processed"

class Message(BaseModel):
    message_id: str
    sender_id: str
    recipient_id: str
    content: Any
    priority: MessagePriority
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = datetime.now()
    processed_at: Optional[datetime] = None

class MessageQueue:
    def __init__(self):
        self._messages: Dict[str, Message] = {}
        self._priority_queues: Dict[MessagePriority, List[str]] = {
            priority: [] for priority in MessagePriority
        }
        self._agent_queues: Dict[str, List[str]] = {}
    
    def enqueue_message(self, message: Message) -> None:
        if message.message_id in self._messages:
            raise ValueError(f"Message {message.message_id} already exists")
        
        self._messages[message.message_id] = message
        self._priority_queues[message.priority].append(message.message_id)
        
        if message.recipient_id not in self._agent_queues:
            self._agent_queues[message.recipient_id] = []
        self._agent_queues[message.recipient_id].append(message.message_id)
    
    def dequeue_message(self, agent_id: str) -> Optional[Message]:
        if agent_id not in self._agent_queues or not self._agent_queues[agent_id]:
            return None
        
        # Get messages in priority order
        for priority in [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                        MessagePriority.MEDIUM, MessagePriority.LOW]:
            for message_id in self._priority_queues[priority]:
                if message_id in self._agent_queues[agent_id]:
                    message = self._messages[message_id]
                    if message.status == MessageStatus.PENDING:
                        message.status = MessageStatus.DELIVERED
                        return message
        
        return None
    
    def get_message(self, message_id: str) -> Optional[Message]:
        return self._messages.get(message_id)
    
    def update_message_status(self, message_id: str, status: MessageStatus) -> None:
        if message_id not in self._messages:
            raise ValueError(f"Message {message_id} not found")
        
        message = self._messages[message_id]
        message.status = status
        if status == MessageStatus.PROCESSED:
            message.processed_at = datetime.now()
    
    def get_messages_by_status(self, status: MessageStatus) -> List[Message]:
        return [
            message for message in self._messages.values()
            if message.status == status
        ]
    
    def get_agent_messages(self, agent_id: str) -> List[Message]:
        if agent_id not in self._agent_queues:
            return []
        
        return [
            self._messages[message_id]
            for message_id in self._agent_queues[agent_id]
        ]
    
    def remove_message(self, message_id: str) -> None:
        if message_id not in self._messages:
            raise ValueError(f"Message {message_id} not found")
        
        message = self._messages[message_id]
        self._priority_queues[message.priority].remove(message_id)
        self._agent_queues[message.recipient_id].remove(message_id)
        del self._messages[message_id]
    
    def clear_processed_messages(self) -> None:
        processed_messages = self.get_messages_by_status(MessageStatus.PROCESSED)
        for message in processed_messages:
            self.remove_message(message.message_id) 