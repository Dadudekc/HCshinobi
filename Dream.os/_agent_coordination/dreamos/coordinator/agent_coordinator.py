"""AgentCoordinator - Master coordinator for the Dream.OS agent system."""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
import json

from dreamos.coordinator import (
    AgentDomain, AgentState, AgentContext, 
    AgentMessage, CoordinationEvent, CoordinationStatus
)

logger = logging.getLogger(__name__)

class AgentCoordinator:
    """Master coordinator for managing agent interactions and workflow."""
    
    def __init__(self, workspace_dir: str, task_dir: str = "agent_tasks"):
        """Initialize the coordinator.
        
        Args:
            workspace_dir: Root workspace directory
            task_dir: Directory for agent task definitions
        """
        self.workspace_dir = Path(workspace_dir)
        self.task_dir = self.workspace_dir / task_dir
        self.task_dir.mkdir(parents=True, exist_ok=True)
        
        self.status = CoordinationStatus()
        self.domain_dependencies = {
            AgentDomain.COORDINATOR: set(),
            AgentDomain.AGENTS: {AgentDomain.COORDINATOR},
            AgentDomain.SOCIAL: {AgentDomain.COORDINATOR},
            AgentDomain.DREAMOS: {AgentDomain.AGENTS, AgentDomain.SOCIAL}
        }
        
        self._message_queue = asyncio.Queue()
        self._event_queue = asyncio.Queue()
        
    async def initialize_cleanup(self) -> None:
        """Initialize the system-wide cleanup operation."""
        logger.info("Initializing system-wide cleanup operation")
        
        # Load task definitions
        tasks = self._load_task_definitions()
        
        # Create initial coordination event
        init_event = CoordinationEvent(
            event_type="cleanup_init",
            source_domain=AgentDomain.COORDINATOR,
            target_domain=AgentDomain.COORDINATOR,
            context={"tasks": tasks},
            timestamp=datetime.utcnow()
        )
        
        await self._event_queue.put(init_event)
        self.status.add_event(init_event)
        
        # Dispatch initial messages to all domains
        for domain in AgentDomain:
            if domain != AgentDomain.COORDINATOR:
                message = AgentMessage(
                    source="coordinator",
                    target=f"{domain.value}_manager",
                    message_type="init_cleanup",
                    content={
                        "tasks": tasks.get(domain.value, []),
                        "dependencies": list(self.domain_dependencies[domain])
                    },
                    timestamp=datetime.utcnow(),
                    requires_response=True
                )
                await self._message_queue.put(message)
                self.status.add_message(message)
    
    def _load_task_definitions(self) -> Dict:
        """Load task definitions for all agents."""
        tasks = {}
        for domain in AgentDomain:
            task_file = self.task_dir / f"{domain.value}_tasks.json"
            if task_file.exists():
                try:
                    with open(task_file, 'r') as f:
                        tasks[domain.value] = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load tasks for {domain}: {e}")
                    tasks[domain.value] = []
        return tasks
    
    async def process_message(self, message: AgentMessage) -> None:
        """Process an incoming agent message.
        
        Args:
            message: AgentMessage to process
        """
        logger.info(f"Processing message from {message.source} to {message.target}")
        
        if message.message_type == "status_update":
            self._handle_status_update(message)
        elif message.message_type == "task_complete":
            await self._handle_task_completion(message)
        elif message.message_type == "error":
            await self._handle_error(message)
            
        # Check if we can progress any waiting domains
        await self._check_domain_progress()
    
    def _handle_status_update(self, message: AgentMessage) -> None:
        """Handle agent status update message."""
        domain = AgentDomain(message.source.split('_')[0])
        state = AgentState(message.content["state"])
        self.status.update_domain_state(domain, state)
        
        if "context" in message.content:
            self.status.update_agent(
                message.source,
                AgentContext(**message.content["context"])
            )
    
    async def _handle_task_completion(self, message: AgentMessage) -> None:
        """Handle task completion message."""
        domain = AgentDomain(message.source.split('_')[0])
        
        # Update relevant events
        for event in self.status.active_events:
            if (event.target_domain == domain and 
                event.context.get("task_id") == message.content.get("task_id")):
                event.status = "completed"
                event.result = message.content.get("result")
        
        # Check if domain has completed all tasks
        if self._are_domain_tasks_complete(domain):
            self.status.update_domain_state(domain, AgentState.IDLE)
            await self._notify_dependent_domains(domain)
    
    async def _handle_error(self, message: AgentMessage) -> None:
        """Handle error message from agent."""
        domain = AgentDomain(message.source.split('_')[0])
        self.status.update_domain_state(domain, AgentState.ERROR)
        
        # Create error event
        error_event = CoordinationEvent(
            event_type="agent_error",
            source_domain=domain,
            target_domain=AgentDomain.COORDINATOR,
            context=message.content,
            timestamp=datetime.utcnow(),
            status="error"
        )
        self.status.add_event(error_event)
        
        # Notify dependent domains
        await self._notify_dependent_domains(domain, error=True)
    
    def _are_domain_tasks_complete(self, domain: AgentDomain) -> bool:
        """Check if all tasks for a domain are complete."""
        domain_agents = self.status.get_domain_agents(domain)
        return all(
            agent.state in (AgentState.IDLE, AgentState.WAITING)
            for agent in domain_agents
        )
    
    async def _notify_dependent_domains(self, domain: AgentDomain, error: bool = False) -> None:
        """Notify domains that depend on the completed domain."""
        for dep_domain in AgentDomain:
            if domain in self.domain_dependencies[dep_domain]:
                message = AgentMessage(
                    source="coordinator",
                    target=f"{dep_domain.value}_manager",
                    message_type="dependency_update",
                    content={
                        "completed_domain": domain.value,
                        "status": "error" if error else "completed"
                    },
                    timestamp=datetime.utcnow()
                )
                await self._message_queue.put(message)
                self.status.add_message(message)
    
    async def _check_domain_progress(self) -> None:
        """Check if any waiting domains can progress."""
        for domain in AgentDomain:
            if self.status.domain_states[domain] == AgentState.WAITING:
                dependencies = self.domain_dependencies[domain]
                if all(
                    self.status.domain_states[dep] == AgentState.IDLE
                    for dep in dependencies
                ):
                    # All dependencies are complete, domain can progress
                    message = AgentMessage(
                        source="coordinator",
                        target=f"{domain.value}_manager",
                        message_type="resume_tasks",
                        content={},
                        timestamp=datetime.utcnow()
                    )
                    await self._message_queue.put(message)
                    self.status.add_message(message)
    
    async def run(self) -> None:
        """Run the coordinator main loop."""
        try:
            while True:
                # Process any pending messages
                while not self._message_queue.empty():
                    message = await self._message_queue.get()
                    await self.process_message(message)
                
                # Process any pending events
                while not self._event_queue.empty():
                    event = await self._event_queue.get()
                    # Handle system-wide events
                    if event.event_type == "cleanup_init":
                        await self.initialize_cleanup()
                
                # Check overall progress
                all_complete = all(
                    state == AgentState.IDLE
                    for state in self.status.domain_states.values()
                )
                
                if all_complete:
                    logger.info("All domains have completed their tasks")
                    break
                
                await asyncio.sleep(1)  # Prevent busy-waiting
                
        except Exception as e:
            logger.error(f"Coordinator error: {e}")
            # Notify all domains of shutdown
            for domain in AgentDomain:
                if domain != AgentDomain.COORDINATOR:
                    message = AgentMessage(
                        source="coordinator",
                        target=f"{domain.value}_manager",
                        message_type="shutdown",
                        content={"reason": str(e)},
                        timestamp=datetime.utcnow()
                    )
                    await self._message_queue.put(message)
            raise 