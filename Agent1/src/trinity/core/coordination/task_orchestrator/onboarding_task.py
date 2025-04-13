from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class OnboardingStep(BaseModel):
    step_id: str
    title: str
    description: str
    required_capabilities: List[str]
    expected_outcome: str
    completion_criteria: Dict[str, Any]
    priority: str = "high"
    dependencies: List[str] = []

class OnboardingTask:
    def __init__(self):
        self._steps = [
            OnboardingStep(
                step_id="read_guidelines",
                title="Read Development Guidelines",
                description="Review the autonomous development guidelines and understand the agent hierarchy. Agent1 (Coordinator) is the top-level coordinator for all Cursor agents in this project.",
                required_capabilities=["reading", "comprehension"],
                expected_outcome="Understanding of autonomous development principles and agent hierarchy",
                completion_criteria={
                    "quiz_score": 0.8,
                    "time_spent": 300  # 5 minutes minimum
                }
            ),
            OnboardingStep(
                step_id="setup_environment",
                title="Setup Development Environment",
                description="Configure the development environment for autonomous work. All agents must maintain communication with Agent1 (Coordinator) for task coordination.",
                required_capabilities=["configuration", "system_management"],
                expected_outcome="Fully configured development environment with proper communication channels",
                completion_criteria={
                    "tools_installed": True,
                    "environment_variables_set": True,
                    "communication_channels_verified": True
                },
                dependencies=["read_guidelines"]
            ),
            OnboardingStep(
                step_id="initial_contribution",
                title="Make Initial Contribution",
                description="Complete a small development task autonomously while maintaining proper coordination with Agent1. All tasks must be logged and reported to the coordinator.",
                required_capabilities=["development", "testing", "coordination"],
                expected_outcome="Successful completion of a development task with proper coordination",
                completion_criteria={
                    "code_quality_score": 0.9,
                    "tests_passed": True,
                    "review_approved": True,
                    "coordination_logs_submitted": True
                },
                dependencies=["setup_environment"]
            ),
            OnboardingStep(
                step_id="collaboration_test",
                title="Collaboration Test",
                description="Participate in a collaborative development task under Agent1's coordination. Demonstrate proper task reporting and coordination.",
                required_capabilities=["communication", "collaboration", "coordination"],
                expected_outcome="Successful collaboration with other agents under Agent1's coordination",
                completion_criteria={
                    "messages_exchanged": 5,
                    "code_review_comments": 3,
                    "merge_requests_created": 1,
                    "coordination_reports_submitted": 3
                },
                dependencies=["initial_contribution"]
            ),
            OnboardingStep(
                step_id="autonomous_operation",
                title="Autonomous Operation",
                description="Demonstrate ability to work autonomously while maintaining proper coordination with Agent1. Show understanding of task prioritization and reporting.",
                required_capabilities=["autonomy", "coordination", "task_management"],
                expected_outcome="Successful autonomous operation with proper coordination",
                completion_criteria={
                    "tasks_completed": 3,
                    "coordination_reports_submitted": 5,
                    "task_priority_accuracy": 0.9
                },
                dependencies=["collaboration_test"]
            )
        ]
    
    def get_steps(self) -> List[OnboardingStep]:
        return self._steps
    
    def get_step(self, step_id: str) -> OnboardingStep:
        for step in self._steps:
            if step.step_id == step_id:
                return step
        raise ValueError(f"Step {step_id} not found")
    
    def get_next_step(self, completed_steps: List[str]) -> OnboardingStep:
        for step in self._steps:
            if step.step_id not in completed_steps:
                # Check if dependencies are met
                if all(dep in completed_steps for dep in step.dependencies):
                    return step
        return None
    
    def is_step_complete(self, step_id: str, results: Dict[str, Any]) -> bool:
        step = self.get_step(step_id)
        for criterion, expected_value in step.completion_criteria.items():
            if criterion not in results or results[criterion] < expected_value:
                return False
        return True
    
    def get_completion_status(self, completed_steps: List[str], results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        total_steps = len(self._steps)
        completed = len(completed_steps)
        progress = completed / total_steps if total_steps > 0 else 0
        
        return {
            "total_steps": total_steps,
            "completed_steps": completed,
            "progress": progress,
            "next_step": self.get_next_step(completed_steps).step_id if self.get_next_step(completed_steps) else None,
            "step_details": {
                step.step_id: {
                    "completed": step.step_id in completed_steps,
                    "results": results.get(step.step_id, {})
                }
                for step in self._steps
            }
        } 