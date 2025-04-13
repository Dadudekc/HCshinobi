"""
Team Coordination Implementation
This module implements the team coordination system for managing team collaboration.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class TeamRole(Enum):
    """Team member roles."""
    DEVELOPER = "developer"
    TESTER = "tester"
    MANAGER = "manager"
    ADMIN = "admin"

class TaskStatus(Enum):
    """Task status values."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"

@dataclass
class TeamMember:
    """Team member data structure."""
    name: str
    role: TeamRole
    skills: List[str]
    availability: float
    current_tasks: List[str]

@dataclass
class TeamTask:
    """Team task data structure."""
    id: str
    title: str
    description: str
    assigned_to: str
    status: TaskStatus
    priority: int
    due_date: datetime
    dependencies: List[str]

class TeamCoordination:
    """Team coordination system for managing team collaboration."""
    
    def __init__(self):
        """Initialize the team coordination system."""
        self.logger = logging.getLogger(__name__)
        self.members: Dict[str, TeamMember] = {}
        self.tasks: Dict[str, TeamTask] = {}
        self._initialize_admin()
        
    def _initialize_admin(self) -> None:
        """Initialize admin team member."""
        self.members["admin"] = TeamMember(
            name="admin",
            role=TeamRole.ADMIN,
            skills=["management", "coordination"],
            availability=1.0,
            current_tasks=[]
        )
        self.logger.info("Admin team member initialized")
        
    def add_member(self,
                  name: str,
                  role: TeamRole,
                  skills: List[str]) -> bool:
        """Add a new team member."""
        if name in self.members:
            return False
            
        self.members[name] = TeamMember(
            name=name,
            role=role,
            skills=skills,
            availability=1.0,
            current_tasks=[]
        )
        self.logger.info(f"Added team member: {name}")
        return True
        
    def remove_member(self, name: str) -> bool:
        """Remove a team member."""
        if name not in self.members:
            return False
            
        # Reassign tasks if needed
        member = self.members[name]
        for task_id in member.current_tasks:
            task = self.tasks[task_id]
            self._reassign_task(task_id)
            
        del self.members[name]
        self.logger.info(f"Removed team member: {name}")
        return True
        
    def _reassign_task(self, task_id: str) -> None:
        """Reassign a task to an available team member."""
        task = self.tasks[task_id]
        available_members = [
            name for name, member in self.members.items()
            if member.availability > 0 and
               name != task.assigned_to
        ]
        
        if available_members:
            new_assignee = available_members[0]
            task.assigned_to = new_assignee
            self.members[new_assignee].current_tasks.append(task_id)
            self.logger.info(f"Reassigned task {task_id} to {new_assignee}")
            
    def create_task(self,
                   title: str,
                   description: str,
                   priority: int,
                   due_date: datetime,
                   dependencies: List[str] = None) -> str:
        """Create a new team task."""
        task_id = f"task_{len(self.tasks) + 1}"
        task = TeamTask(
            id=task_id,
            title=title,
            description=description,
            assigned_to="",
            status=TaskStatus.TODO,
            priority=priority,
            due_date=due_date,
            dependencies=dependencies or []
        )
        
        self.tasks[task_id] = task
        self._assign_task(task_id)
        self.logger.info(f"Created task: {title}")
        return task_id
        
    def _assign_task(self, task_id: str) -> None:
        """Assign a task to an available team member."""
        task = self.tasks[task_id]
        available_members = [
            name for name, member in self.members.items()
            if member.availability > 0
        ]
        
        if available_members:
            assignee = available_members[0]
            task.assigned_to = assignee
            task.status = TaskStatus.IN_PROGRESS
            self.members[assignee].current_tasks.append(task_id)
            self.members[assignee].availability -= 0.2  # Reduce availability
            self.logger.info(f"Assigned task {task_id} to {assignee}")
            
    def update_task_status(self,
                         task_id: str,
                         status: TaskStatus) -> bool:
        """Update task status."""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        old_status = task.status
        task.status = status
        
        if status == TaskStatus.DONE:
            member = self.members[task.assigned_to]
            member.current_tasks.remove(task_id)
            member.availability += 0.2  # Increase availability
            
        self.logger.info(f"Updated task {task_id} status: {old_status} -> {status}")
        return True
        
    def get_member_tasks(self, member_name: str) -> List[TeamTask]:
        """Get tasks assigned to a team member."""
        if member_name not in self.members:
            return []
            
        return [
            self.tasks[task_id]
            for task_id in self.members[member_name].current_tasks
        ]
        
    def get_team_status(self) -> Dict[str, Any]:
        """Get comprehensive team status."""
        return {
            "members": {
                name: {
                    "role": member.role.value,
                    "availability": member.availability,
                    "current_tasks": len(member.current_tasks)
                }
                for name, member in self.members.items()
            },
            "tasks": {
                "total": len(self.tasks),
                "todo": len([t for t in self.tasks.values() 
                           if t.status == TaskStatus.TODO]),
                "in_progress": len([t for t in self.tasks.values() 
                                  if t.status == TaskStatus.IN_PROGRESS]),
                "review": len([t for t in self.tasks.values() 
                             if t.status == TaskStatus.REVIEW]),
                "done": len([t for t in self.tasks.values() 
                           if t.status == TaskStatus.DONE]),
                "blocked": len([t for t in self.tasks.values() 
                              if t.status == TaskStatus.BLOCKED])
            }
        }
        
    def update_member_availability(self,
                                 member_name: str,
                                 availability: float) -> bool:
        """Update team member availability."""
        if member_name not in self.members:
            return False
            
        self.members[member_name].availability = max(0.0, min(1.0, availability))
        self.logger.info(f"Updated {member_name} availability: {availability}")
        return True 