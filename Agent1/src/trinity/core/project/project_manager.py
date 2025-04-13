"""
Project Management Framework
Manages project lifecycle, milestones, and resources.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
from enum import Enum

class ProjectStatus(Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MilestoneStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"

@dataclass
class Resource:
    id: str
    name: str
    type: str
    capacity: float
    cost_per_hour: float
    allocated_hours: float = 0
    availability: float = 1.0

@dataclass
class Milestone:
    id: str
    name: str
    description: str
    due_date: datetime
    status: MilestoneStatus
    dependencies: List[str]
    deliverables: List[str]
    assigned_resources: List[str]
    progress: float = 0.0
    actual_completion: Optional[datetime] = None

@dataclass
class Risk:
    id: str
    description: str
    probability: float  # 0.0 to 1.0
    impact: float  # 0.0 to 1.0
    mitigation_strategy: str
    status: str
    owner: str

class ProjectManager:
    def __init__(self,
                 project_id: str,
                 name: str,
                 start_date: datetime,
                 end_date: datetime,
                 budget: float,
                 log_dir: str = "logs/project"):
        self.project_id = project_id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.budget = budget
        self.status = ProjectStatus.PLANNING
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = self._setup_logging()
        
        self.milestones: Dict[str, Milestone] = {}
        self.resources: Dict[str, Resource] = {}
        self.risks: Dict[str, Risk] = {}
        self.expenses: List[Dict[str, Any]] = []
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for project management."""
        logger = logging.getLogger(f"project_{self.project_id}")
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler = logging.FileHandler(
            self.log_dir / f"project_{self.project_id}.log"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
        
    def add_milestone(self, id: str, name: str, description: str,
                     due_date: datetime, dependencies: List[str],
                     deliverables: List[str], assigned_resources: List[str]):
        """Add a project milestone."""
        milestone = Milestone(
            id=id,
            name=name,
            description=description,
            due_date=due_date,
            status=MilestoneStatus.PENDING,
            dependencies=dependencies,
            deliverables=deliverables,
            assigned_resources=assigned_resources
        )
        
        self.milestones[id] = milestone
        self.logger.info(f"Added milestone: {name}")
        
    def update_milestone_status(self, milestone_id: str,
                              status: MilestoneStatus,
                              progress: float = None):
        """Update milestone status and progress."""
        if milestone_id not in self.milestones:
            raise ValueError("Invalid milestone ID")
            
        milestone = self.milestones[milestone_id]
        milestone.status = status
        
        if progress is not None:
            milestone.progress = progress
            
        if status == MilestoneStatus.COMPLETED:
            milestone.actual_completion = datetime.now()
            
        self.logger.info(
            f"Updated milestone {milestone_id}: "
            f"status={status.value}, progress={progress}"
        )
        
    def add_resource(self, id: str, name: str, type: str,
                    capacity: float, cost_per_hour: float):
        """Add a project resource."""
        resource = Resource(
            id=id,
            name=name,
            type=type,
            capacity=capacity,
            cost_per_hour=cost_per_hour
        )
        
        self.resources[id] = resource
        self.logger.info(f"Added resource: {name}")
        
    def allocate_resource(self, resource_id: str, hours: float):
        """Allocate hours to a resource."""
        if resource_id not in self.resources:
            raise ValueError("Invalid resource ID")
            
        resource = self.resources[resource_id]
        resource.allocated_hours += hours
        resource.availability = max(
            0.0,
            1.0 - (resource.allocated_hours / resource.capacity)
        )
        
        self.logger.info(
            f"Allocated {hours} hours to resource {resource_id}"
        )
        
    def add_risk(self, id: str, description: str, probability: float,
                 impact: float, mitigation_strategy: str, owner: str):
        """Add a project risk."""
        risk = Risk(
            id=id,
            description=description,
            probability=probability,
            impact=impact,
            mitigation_strategy=mitigation_strategy,
            status="identified",
            owner=owner
        )
        
        self.risks[id] = risk
        self.logger.info(f"Added risk: {description}")
        
    def update_risk_status(self, risk_id: str, status: str):
        """Update risk status."""
        if risk_id not in self.risks:
            raise ValueError("Invalid risk ID")
            
        self.risks[risk_id].status = status
        self.logger.info(f"Updated risk {risk_id} status: {status}")
        
    def record_expense(self, description: str, amount: float,
                      category: str, date: datetime):
        """Record a project expense."""
        expense = {
            "description": description,
            "amount": amount,
            "category": category,
            "date": date.isoformat()
        }
        
        self.expenses.append(expense)
        self.logger.info(f"Recorded expense: {description} ({amount})")
        
    def get_project_status(self) -> Dict[str, Any]:
        """Get comprehensive project status."""
        total_milestones = len(self.milestones)
        completed_milestones = sum(
            1 for m in self.milestones.values()
            if m.status == MilestoneStatus.COMPLETED
        )
        
        total_expenses = sum(e["amount"] for e in self.expenses)
        budget_remaining = self.budget - total_expenses
        
        active_risks = sum(
            1 for r in self.risks.values()
            if r.status in ["identified", "active"]
        )
        
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value,
            "progress": completed_milestones / total_milestones if total_milestones > 0 else 0,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days_remaining": (self.end_date - datetime.now()).days,
            "budget": {
                "total": self.budget,
                "spent": total_expenses,
                "remaining": budget_remaining,
                "percent_used": (total_expenses / self.budget * 100) if self.budget > 0 else 0
            },
            "milestones": {
                "total": total_milestones,
                "completed": completed_milestones,
                "in_progress": sum(1 for m in self.milestones.values() if m.status == MilestoneStatus.IN_PROGRESS),
                "delayed": sum(1 for m in self.milestones.values() if m.status == MilestoneStatus.DELAYED)
            },
            "resources": {
                "total": len(self.resources),
                "fully_allocated": sum(1 for r in self.resources.values() if r.availability < 0.1),
                "available": sum(1 for r in self.resources.values() if r.availability > 0.5)
            },
            "risks": {
                "total": len(self.risks),
                "active": active_risks,
                "mitigated": sum(1 for r in self.risks.values() if r.status == "mitigated")
            }
        }
        
    def get_critical_path(self) -> List[Milestone]:
        """Calculate critical path through project milestones."""
        def get_dependencies(milestone_id: str) -> List[Milestone]:
            milestone = self.milestones[milestone_id]
            return [
                self.milestones[dep_id]
                for dep_id in milestone.dependencies
                if dep_id in self.milestones
            ]
            
        def calculate_path(milestone: Milestone, path: List[Milestone]) -> List[Milestone]:
            if not milestone.dependencies:
                return path + [milestone]
                
            longest_path = path + [milestone]
            for dep_id in milestone.dependencies:
                if dep_id in self.milestones:
                    dep_path = calculate_path(self.milestones[dep_id], path)
                    if len(dep_path) > len(longest_path):
                        longest_path = dep_path
                        
            return longest_path
            
        end_milestones = [
            m for m in self.milestones.values()
            if not any(m.id in other.dependencies for other in self.milestones.values())
        ]
        
        critical_path = []
        for end_milestone in end_milestones:
            path = calculate_path(end_milestone, [])
            if len(path) > len(critical_path):
                critical_path = path
                
        return critical_path
        
    def export_project_data(self, output_file: Optional[str] = None):
        """Export project data to JSON file."""
        if output_file is None:
            output_file = self.log_dir / f"project_{self.project_id}_{datetime.now():%Y%m%d_%H%M%S}.json"
            
        data = {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "budget": self.budget,
            "milestones": {
                id: {
                    "name": m.name,
                    "description": m.description,
                    "due_date": m.due_date.isoformat(),
                    "status": m.status.value,
                    "progress": m.progress,
                    "dependencies": m.dependencies,
                    "deliverables": m.deliverables,
                    "assigned_resources": m.assigned_resources,
                    "actual_completion": m.actual_completion.isoformat() if m.actual_completion else None
                }
                for id, m in self.milestones.items()
            },
            "resources": {
                id: {
                    "name": r.name,
                    "type": r.type,
                    "capacity": r.capacity,
                    "cost_per_hour": r.cost_per_hour,
                    "allocated_hours": r.allocated_hours,
                    "availability": r.availability
                }
                for id, r in self.resources.items()
            },
            "risks": {
                id: {
                    "description": r.description,
                    "probability": r.probability,
                    "impact": r.impact,
                    "mitigation_strategy": r.mitigation_strategy,
                    "status": r.status,
                    "owner": r.owner
                }
                for id, r in self.risks.items()
            },
            "expenses": self.expenses
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        self.logger.info(f"Exported project data to {output_file}")
        
    def generate_status_report(self) -> str:
        """Generate a formatted status report."""
        status = self.get_project_status()
        
        report = f"""
Project Status Report
====================
Project: {self.name} ({self.project_id})
Status: {self.status.value}
Generated: {datetime.now():%Y-%m-%d %H:%M:%S}

Timeline
--------
Start Date: {self.start_date:%Y-%m-%d}
End Date: {self.end_date:%Y-%m-%d}
Days Remaining: {status['days_remaining']}
Overall Progress: {status['progress']:.1%}

Budget
------
Total Budget: ${status['budget']['total']:,.2f}
Spent: ${status['budget']['spent']:,.2f}
Remaining: ${status['budget']['remaining']:,.2f}
Budget Utilization: {status['budget']['percent_used']:.1f}%

Milestones
----------
Total: {status['milestones']['total']}
Completed: {status['milestones']['completed']}
In Progress: {status['milestones']['in_progress']}
Delayed: {status['milestones']['delayed']}

Resources
---------
Total Resources: {status['resources']['total']}
Fully Allocated: {status['resources']['fully_allocated']}
Available: {status['resources']['available']}

Risks
-----
Total Risks: {status['risks']['total']}
Active Risks: {status['risks']['active']}
Mitigated: {status['risks']['mitigated']}

Critical Path Milestones
-----------------------"""
        
        for milestone in self.get_critical_path():
            report += f"""
- {milestone.name}
  Due: {milestone.due_date:%Y-%m-%d}
  Status: {milestone.status.value}
  Progress: {milestone.progress:.1%}"""
            
        return report 