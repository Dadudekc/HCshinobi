"""
Project Management Implementation
This module implements the project management system for tracking project progress and resources.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

class ProjectStatus(Enum):
    """Project status values."""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

class MilestoneStatus(Enum):
    """Milestone status values."""
    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"

@dataclass
class Milestone:
    """Milestone data structure."""
    id: str
    title: str
    description: str
    due_date: datetime
    status: MilestoneStatus
    tasks: List[str]
    dependencies: List[str]

@dataclass
class Project:
    """Project data structure."""
    id: str
    name: str
    description: str
    status: ProjectStatus
    start_date: datetime
    end_date: datetime
    budget: float
    milestones: Dict[str, Milestone]
    team_members: List[str]
    resources: Dict[str, float]

class ProjectManagement:
    """Project management system for tracking project progress and resources."""
    
    def __init__(self):
        """Initialize the project management system."""
        self.logger = logging.getLogger(__name__)
        self.projects: Dict[str, Project] = {}
        self._initialize_system()
        
    def _initialize_system(self) -> None:
        """Initialize system with default project."""
        default_project = Project(
            id="default",
            name="System Implementation",
            description="Core system implementation project",
            status=ProjectStatus.IN_PROGRESS,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            budget=100000.0,
            milestones={},
            team_members=[],
            resources={}
        )
        self.projects["default"] = default_project
        self.logger.info("Project management system initialized")
        
    def create_project(self,
                      name: str,
                      description: str,
                      start_date: datetime,
                      end_date: datetime,
                      budget: float) -> str:
        """Create a new project."""
        project_id = f"project_{len(self.projects) + 1}"
        project = Project(
            id=project_id,
            name=name,
            description=description,
            status=ProjectStatus.PLANNING,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            milestones={},
            team_members=[],
            resources={}
        )
        self.projects[project_id] = project
        self.logger.info(f"Created project: {name}")
        return project_id
        
    def add_milestone(self,
                     project_id: str,
                     title: str,
                     description: str,
                     due_date: datetime,
                     dependencies: List[str] = None) -> str:
        """Add a milestone to a project."""
        if project_id not in self.projects:
            return ""
            
        milestone_id = f"milestone_{len(self.projects[project_id].milestones) + 1}"
        milestone = Milestone(
            id=milestone_id,
            title=title,
            description=description,
            due_date=due_date,
            status=MilestoneStatus.UPCOMING,
            tasks=[],
            dependencies=dependencies or []
        )
        
        self.projects[project_id].milestones[milestone_id] = milestone
        self.logger.info(f"Added milestone {title} to project {project_id}")
        return milestone_id
        
    def update_milestone_status(self,
                              project_id: str,
                              milestone_id: str,
                              status: MilestoneStatus) -> bool:
        """Update milestone status."""
        if (project_id not in self.projects or
            milestone_id not in self.projects[project_id].milestones):
            return False
            
        milestone = self.projects[project_id].milestones[milestone_id]
        old_status = milestone.status
        milestone.status = status
        
        self.logger.info(
            f"Updated milestone {milestone_id} status: {old_status} -> {status}"
        )
        return True
        
    def add_team_member(self,
                       project_id: str,
                       member_name: str) -> bool:
        """Add a team member to a project."""
        if project_id not in self.projects:
            return False
            
        if member_name in self.projects[project_id].team_members:
            return False
            
        self.projects[project_id].team_members.append(member_name)
        self.logger.info(f"Added team member {member_name} to project {project_id}")
        return True
        
    def allocate_resources(self,
                         project_id: str,
                         resource_type: str,
                         amount: float) -> bool:
        """Allocate resources to a project."""
        if project_id not in self.projects:
            return False
            
        self.projects[project_id].resources[resource_type] = amount
        self.logger.info(
            f"Allocated {amount} of {resource_type} to project {project_id}"
        )
        return True
        
    def update_project_status(self,
                            project_id: str,
                            status: ProjectStatus) -> bool:
        """Update project status."""
        if project_id not in self.projects:
            return False
            
        old_status = self.projects[project_id].status
        self.projects[project_id].status = status
        
        self.logger.info(
            f"Updated project {project_id} status: {old_status} -> {status}"
        )
        return True
        
    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive project status."""
        if project_id not in self.projects:
            return None
            
        project = self.projects[project_id]
        return {
            "id": project.id,
            "name": project.name,
            "status": project.status.value,
            "progress": self._calculate_progress(project),
            "milestones": {
                mid: {
                    "title": m.title,
                    "status": m.status.value,
                    "due_date": m.due_date.isoformat(),
                    "tasks": len(m.tasks)
                }
                for mid, m in project.milestones.items()
            },
            "team": {
                "members": project.team_members,
                "count": len(project.team_members)
            },
            "resources": project.resources,
            "budget": {
                "total": project.budget,
                "used": sum(project.resources.values()),
                "remaining": project.budget - sum(project.resources.values())
            }
        }
        
    def _calculate_progress(self, project: Project) -> float:
        """Calculate project progress based on milestones."""
        if not project.milestones:
            return 0.0
            
        completed = sum(
            1 for m in project.milestones.values()
            if m.status == MilestoneStatus.COMPLETED
        )
        return (completed / len(project.milestones)) * 100
        
    def get_project_timeline(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project timeline with milestones."""
        if project_id not in self.projects:
            return None
            
        project = self.projects[project_id]
        return {
            "start_date": project.start_date.isoformat(),
            "end_date": project.end_date.isoformat(),
            "duration_days": (project.end_date - project.start_date).days,
            "milestones": [
                {
                    "id": mid,
                    "title": m.title,
                    "due_date": m.due_date.isoformat(),
                    "status": m.status.value,
                    "dependencies": m.dependencies
                }
                for mid, m in sorted(
                    project.milestones.items(),
                    key=lambda x: x[1].due_date
                )
            ]
        } 