from typing import Dict, List, Optional
from .message_queue import Message, MessageQueue, MessageStatus
from ..agent_manager.agent_registry import AgentRegistry

class MessageRouter:
    def __init__(self, message_queue: MessageQueue, agent_registry: AgentRegistry):
        self._message_queue = message_queue
        self._agent_registry = agent_registry
        self._routing_rules: Dict[str, List[str]] = {}
    
    def send_message(self, sender_id: str, recipient_id: str, content: Any, 
                    priority: MessagePriority) -> Message:
        # Validate sender and recipient
        if not self._agent_registry.get_agent(sender_id):
            raise ValueError(f"Sender {sender_id} not found")
        
        if not self._agent_registry.get_agent(recipient_id):
            raise ValueError(f"Recipient {recipient_id} not found")
        
        # Create and enqueue message
        message = Message(
            message_id=f"msg_{len(self._message_queue._messages)}",
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
            priority=priority
        )
        
        self._message_queue.enqueue_message(message)
        return message
    
    def broadcast_message(self, sender_id: str, content: Any, 
                         priority: MessagePriority) -> List[Message]:
        messages = []
        for agent in self._agent_registry.get_all_agents():
            if agent.agent_id != sender_id:
                message = self.send_message(
                    sender_id=sender_id,
                    recipient_id=agent.agent_id,
                    content=content,
                    priority=priority
                )
                messages.append(message)
        return messages
    
    def route_message(self, message: Message) -> None:
        # Apply routing rules if any
        if message.recipient_id in self._routing_rules:
            for rule_recipient in self._routing_rules[message.recipient_id]:
                # Create a copy of the message for each rule recipient
                rule_message = Message(
                    message_id=f"{message.message_id}_rule_{len(self._message_queue._messages)}",
                    sender_id=message.sender_id,
                    recipient_id=rule_recipient,
                    content=message.content,
                    priority=message.priority
                )
                self._message_queue.enqueue_message(rule_message)
    
    def add_routing_rule(self, recipient_id: str, rule_recipients: List[str]) -> None:
        if recipient_id not in self._routing_rules:
            self._routing_rules[recipient_id] = []
        self._routing_rules[recipient_id].extend(rule_recipients)
    
    def remove_routing_rule(self, recipient_id: str, rule_recipient: str) -> None:
        if recipient_id in self._routing_rules:
            if rule_recipient in self._routing_rules[recipient_id]:
                self._routing_rules[recipient_id].remove(rule_recipient)
    
    def get_routing_rules(self, recipient_id: str) -> List[str]:
        return self._routing_rules.get(recipient_id, [])
    
    def get_undelivered_messages(self, agent_id: str) -> List[Message]:
        return [
            message for message in self._message_queue.get_agent_messages(agent_id)
            if message.status == MessageStatus.PENDING
        ]
    
    def acknowledge_message(self, message_id: str) -> None:
        self._message_queue.update_message_status(
            message_id=message_id,
            status=MessageStatus.PROCESSED
        ) 