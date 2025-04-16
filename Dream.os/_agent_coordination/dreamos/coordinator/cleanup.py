"""Cleanup manager for Dream.OS agent coordination system."""

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from dreamos.coordinator import AgentDomain, AgentState

logger = logging.getLogger(__name__)

@dataclass
class CleanupTask:
    """Represents a cleanup task with its metadata."""
    name: str
    domain: AgentDomain
    description: str
    dependencies: List[AgentDomain]
    impact_level: str
    target_files: List[str]
    
class CleanupManager:
    """Manages system-wide cleanup operations."""
    
    def __init__(self, workspace_dir: Path, task_dir: Path):
        self.workspace_dir = workspace_dir
        self.task_dir = task_dir
        self.tasks: Dict[AgentDomain, List[CleanupTask]] = {}
        self._load_tasks()
        
    def _load_tasks(self) -> None:
        """Load cleanup tasks from task directory."""
        try:
            for task_file in self.task_dir.glob("*.json"):
                with open(task_file) as f:
                    task_data = json.load(f)
                    
                domain = AgentDomain(task_data["domain"])
                task = CleanupTask(
                    name=task_data["name"],
                    domain=domain,
                    description=task_data["description"],
                    dependencies=[AgentDomain(d) for d in task_data.get("dependencies", [])],
                    impact_level=task_data.get("impact_level", "low"),
                    target_files=task_data.get("target_files", [])
                )
                
                if domain not in self.tasks:
                    self.tasks[domain] = []
                self.tasks[domain].append(task)
                
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            raise
            
    async def get_tasks(self) -> List[CleanupTask]:
        """Get all cleanup tasks."""
        tasks = []
        for domain_tasks in self.tasks.values():
            tasks.extend(domain_tasks)
        return tasks
        
    async def run(self) -> None:
        """Run cleanup tasks in dependency order."""
        processed_domains = set()
        
        while len(processed_domains) < len(AgentDomain):
            for domain in AgentDomain:
                if domain in processed_domains:
                    continue
                    
                # Check if all dependencies are processed
                deps = self._get_domain_dependencies(domain)
                if not all(d in processed_domains for d in deps):
                    continue
                    
                await self._process_domain(domain)
                processed_domains.add(domain)
                
    def _get_domain_dependencies(self, domain: AgentDomain) -> List[AgentDomain]:
        """Get dependencies for a domain based on its tasks."""
        if domain not in self.tasks:
            return []
            
        deps = set()
        for task in self.tasks[domain]:
            deps.update(task.dependencies)
        return list(deps)
        
    async def _process_domain(self, domain: AgentDomain) -> None:
        """Process all tasks for a given domain."""
        if domain not in self.tasks:
            logger.info(f"No tasks found for domain {domain.value}")
            return
            
        logger.info(f"Processing tasks for domain {domain.value}")
        for task in self.tasks[domain]:
            try:
                await self._execute_task(task)
            except Exception as e:
                logger.error(f"Error executing task {task.name}: {e}")
                raise
                
    async def _execute_task(self, task: CleanupTask) -> None:
        """Execute a single cleanup task."""
        logger.info(f"Executing task: {task.name}")
        
        # Validate target files exist
        for file_path in task.target_files:
            full_path = self.workspace_dir / file_path
            if not full_path.exists():
                logger.warning(f"Target file does not exist: {file_path}")
                continue
                
        # Simulate task execution with delay
        await asyncio.sleep(1)
        logger.info(f"Completed task: {task.name}") 