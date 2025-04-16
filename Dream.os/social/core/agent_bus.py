"""Agent Bus for coordinating communication between agents."""

import os
import json
import uuid
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from queue import Queue
from threading import Lock

from social.utils.mailbox_handler import MailboxHandler
from social.exceptions import AgentError
from dreamforge.core.governance_memory_engine import log_event

logger = logging.getLogger(__name__)

class AgentBus:
    """Central message bus for agent coordination and communication."""

    def __init__(self, mailbox_base_dir: str):
        """Initialize the agent bus.
        
        Args:
            mailbox_base_dir: Base directory for agent mailboxes
        """
        self.mailbox_base_dir = mailbox_base_dir
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.message_queues: Dict[str, Queue] = {}
        self.handlers: Dict[str, Dict[str, Callable]] = {}
        self.lock = Lock()
        self._source = "AgentBus"
        
        # Ensure mailbox directory exists
        os.makedirs(mailbox_base_dir, exist_ok=True)
        log_event("BUS_INIT", self._source, {"mailbox_dir": mailbox_base_dir})

    def register_agent(self, agent_id: str, capabilities: List[str], handler_map: Dict[str, Callable]) -> bool:
        """Register an agent with the bus.
        
        Args:
            agent_id: Unique identifier for the agent
            capabilities: List of capabilities the agent provides
            handler_map: Mapping of message types to handler functions
            
        Returns:
            bool: True if registration successful
        """
        with self.lock:
            if agent_id in self.registered_agents:
                log_event("BUS_WARNING", self._source, {
                    "warning": "Agent already registered",
                    "agent_id": agent_id
                })
                return False

            # Create agent's mailbox directories
            inbox_dir = os.path.join(self.mailbox_base_dir, agent_id, "inbox")
            outbox_dir = os.path.join(self.mailbox_base_dir, agent_id, "outbox")
            os.makedirs(inbox_dir, exist_ok=True)
            os.makedirs(outbox_dir, exist_ok=True)

            # Initialize mailbox handler and message queue
            mailbox = MailboxHandler(inbox_dir, outbox_dir)
            message_queue = Queue()

            self.registered_agents[agent_id] = {
                "capabilities": capabilities,
                "mailbox": mailbox,
                "status": "active"
            }
            self.message_queues[agent_id] = message_queue
            self.handlers[agent_id] = handler_map

            log_event("BUS_AGENT_REGISTERED", self._source, {
                "agent_id": agent_id,
                "capabilities": capabilities
            })
            return True

    def deregister_agent(self, agent_id: str) -> bool:
        """Deregister an agent from the bus.
        
        Args:
            agent_id: ID of agent to deregister
            
        Returns:
            bool: True if deregistration successful
        """
        with self.lock:
            if agent_id not in self.registered_agents:
                return False

            # Clean up agent resources
            del self.registered_agents[agent_id]
            del self.message_queues[agent_id]
            del self.handlers[agent_id]

            log_event("BUS_AGENT_DEREGISTERED", self._source, {"agent_id": agent_id})
            return True

    def send_message(self, from_agent: str, to_agent: str, message_type: str, payload: Dict[str, Any]) -> bool:
        """Send a message from one agent to another.
        
        Args:
            from_agent: ID of sending agent
            to_agent: ID of receiving agent
            message_type: Type of message
            payload: Message payload
            
        Returns:
            bool: True if message sent successfully
        """
        if to_agent not in self.registered_agents:
            log_event("BUS_ERROR", self._source, {
                "error": "Recipient agent not registered",
                "to_agent": to_agent
            })
            return False

        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "type": message_type,
            "payload": payload
        }

        try:
            # Add to recipient's queue and mailbox
            self.message_queues[to_agent].put(message)
            self.registered_agents[to_agent]["mailbox"].send_message(message)
            
            log_event("BUS_MESSAGE_SENT", self._source, {
                "message_id": message["message_id"],
                "from": from_agent,
                "to": to_agent,
                "type": message_type
            })
            return True
        except Exception as e:
            log_event("BUS_ERROR", self._source, {
                "error": "Failed to send message",
                "details": str(e),
                "message_id": message["message_id"]
            })
            return False

    def broadcast_message(self, from_agent: str, message_type: str, payload: Dict[str, Any], 
                        capability_filter: Optional[str] = None) -> Dict[str, bool]:
        """Broadcast a message to all registered agents, optionally filtered by capability.
        
        Args:
            from_agent: ID of broadcasting agent
            message_type: Type of message
            payload: Message payload
            capability_filter: Optional capability to filter recipients
            
        Returns:
            Dict[str, bool]: Map of agent IDs to send success status
        """
        results = {}
        for agent_id, info in self.registered_agents.items():
            if agent_id == from_agent:
                continue
            
            if capability_filter and capability_filter not in info["capabilities"]:
                continue

            success = self.send_message(from_agent, agent_id, message_type, payload)
            results[agent_id] = success

        log_event("BUS_BROADCAST", self._source, {
            "from": from_agent,
            "type": message_type,
            "results": results,
            "capability_filter": capability_filter
        })
        return results

    def process_messages(self, agent_id: str, max_messages: int = 10) -> int:
        """Process pending messages for an agent.
        
        Args:
            agent_id: ID of agent to process messages for
            max_messages: Maximum number of messages to process
            
        Returns:
            int: Number of messages processed
        """
        if agent_id not in self.registered_agents:
            raise AgentError(f"Agent {agent_id} not registered")

        processed = 0
        queue = self.message_queues[agent_id]
        handlers = self.handlers[agent_id]

        while not queue.empty() and processed < max_messages:
            message = queue.get()
            message_type = message["type"]

            if message_type in handlers:
                try:
                    handlers[message_type](message["payload"])
                    processed += 1
                    log_event("BUS_MESSAGE_PROCESSED", self._source, {
                        "message_id": message["message_id"],
                        "agent_id": agent_id,
                        "type": message_type
                    })
                except Exception as e:
                    log_event("BUS_ERROR", self._source, {
                        "error": "Message handler failed",
                        "agent_id": agent_id,
                        "message_id": message["message_id"],
                        "details": str(e)
                    })
            else:
                log_event("BUS_WARNING", self._source, {
                    "warning": "No handler for message type",
                    "agent_id": agent_id,
                    "type": message_type
                })

        return processed

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for an agent.
        
        Args:
            agent_id: ID of agent to get status for
            
        Returns:
            Optional[Dict[str, Any]]: Agent status info or None if not found
        """
        if agent_id not in self.registered_agents:
            return None

        agent_info = self.registered_agents[agent_id]
        queue_size = self.message_queues[agent_id].qsize()

        return {
            "agent_id": agent_id,
            "status": agent_info["status"],
            "capabilities": agent_info["capabilities"],
            "pending_messages": queue_size
        }

    def find_first_agent_by_capability(self, capability: str) -> Optional[str]:
        """Find the ID of the first registered agent providing the given capability.
        
        Args:
            capability: The capability to search for.
            
        Returns:
            Optional[str]: The agent ID if found, else None.
        """
        with self.lock:
            for agent_id, info in self.registered_agents.items():
                if capability in info.get("capabilities", []):
                    logger.info(f"Found agent '{agent_id}' providing capability '{capability}'")
                    return agent_id
        logger.warning(f"No registered agent found providing capability '{capability}'")
        return None

    def get_all_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all registered agents.
        
        Returns:
            Dict[str, Dict[str, Any]]: Map of agent IDs to status info
        """
        return {
            agent_id: self.get_agent_status(agent_id)
            for agent_id in self.registered_agents
        } 