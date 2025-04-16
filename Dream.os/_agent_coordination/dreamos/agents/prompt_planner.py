"""PromptPlannerAgent - Breaks down tasks into executable ChatGPT prompts."""

import logging
from typing import Dict, List, Optional
from pathlib import Path
import json
from datetime import datetime

from dreamos.agents import TaskMetadata, PromptPlan

logger = logging.getLogger(__name__)

class PromptPlannerAgent:
    """Agent responsible for planning and structuring prompts for tasks."""
    
    def __init__(self, prompts_dir: str = "queue/prompts"):
        """Initialize the PromptPlannerAgent.
        
        Args:
            prompts_dir: Directory for storing prompt plans
        """
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        
    def create_prompt_plan(self, task: TaskMetadata) -> List[PromptPlan]:
        """Create a sequence of prompts for executing a task.
        
        Args:
            task: TaskMetadata object to create prompts for
            
        Returns:
            List of PromptPlan objects representing the execution sequence
        """
        prompt_plans = []
        
        # Initial analysis prompt
        analysis_prompt = PromptPlan(
            prompt_id=f"{task.task_id}_analysis",
            task_id=task.task_id,
            context={
                "phase": "analysis",
                "files": task.target_files,
                "description": "Analyze current code and plan changes"
            },
            file_targets=task.target_files,
            intent="Analyze current implementation and propose changes",
            dependencies=[],
            execution_order=0
        )
        prompt_plans.append(analysis_prompt)
        
        # Implementation prompts (one per file)
        for idx, file_path in enumerate(task.target_files, 1):
            implement_prompt = PromptPlan(
                prompt_id=f"{task.task_id}_implement_{idx}",
                task_id=task.task_id,
                context={
                    "phase": "implementation",
                    "file": file_path,
                    "description": f"Implement changes for {file_path}"
                },
                file_targets=[file_path],
                intent="Implement proposed changes",
                dependencies=[analysis_prompt.prompt_id],
                execution_order=idx
            )
            prompt_plans.append(implement_prompt)
            
        # Validation prompt
        validation_prompt = PromptPlan(
            prompt_id=f"{task.task_id}_validation",
            task_id=task.task_id,
            context={
                "phase": "validation",
                "files": task.target_files,
                "success_criteria": task.success_criteria,
                "description": "Validate implemented changes"
            },
            file_targets=task.target_files,
            intent="Validate changes against success criteria",
            dependencies=[p.prompt_id for p in prompt_plans],
            execution_order=len(prompt_plans)
        )
        prompt_plans.append(validation_prompt)
        
        # Save prompt plan
        self._save_prompt_plan(task.task_id, prompt_plans)
        return prompt_plans
    
    def _save_prompt_plan(self, task_id: str, prompts: List[PromptPlan]) -> None:
        """Save prompt plan to file.
        
        Args:
            task_id: ID of the task
            prompts: List of PromptPlan objects to save
        """
        plan_file = self.prompts_dir / f"plan_{task_id}.json"
        try:
            with open(plan_file, 'w') as f:
                json.dump(
                    {
                        "task_id": task_id,
                        "created_at": datetime.utcnow().isoformat(),
                        "prompts": [
                            {
                                "prompt_id": p.prompt_id,
                                "task_id": p.task_id,
                                "context": p.context,
                                "file_targets": p.file_targets,
                                "intent": p.intent,
                                "dependencies": p.dependencies,
                                "execution_order": p.execution_order,
                                "status": p.status
                            }
                            for p in prompts
                        ]
                    },
                    f,
                    indent=2
                )
            logger.info(f"Saved prompt plan for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to save prompt plan: {e}")
    
    def load_prompt_plan(self, task_id: str) -> Optional[List[PromptPlan]]:
        """Load prompt plan for a task.
        
        Args:
            task_id: ID of the task to load prompts for
            
        Returns:
            List of PromptPlan objects if found, None otherwise
        """
        plan_file = self.prompts_dir / f"plan_{task_id}.json"
        if not plan_file.exists():
            return None
            
        try:
            with open(plan_file, 'r') as f:
                data = json.load(f)
                return [PromptPlan(**p) for p in data["prompts"]]
        except Exception as e:
            logger.error(f"Failed to load prompt plan: {e}")
            return None
    
    def get_next_prompt(self, task_id: str) -> Optional[PromptPlan]:
        """Get the next prompt ready for execution.
        
        Args:
            task_id: ID of the task to get next prompt for
            
        Returns:
            PromptPlan object if ready, None otherwise
        """
        prompts = self.load_prompt_plan(task_id)
        if not prompts:
            return None
            
        for prompt in sorted(prompts, key=lambda p: p.execution_order):
            if prompt.status == "pending":
                return prompt
        
        return None
    
    def update_prompt_status(self, prompt_id: str, task_id: str, status: str) -> None:
        """Update status of a prompt.
        
        Args:
            prompt_id: ID of the prompt to update
            task_id: ID of the task the prompt belongs to
            status: New status value
        """
        prompts = self.load_prompt_plan(task_id)
        if not prompts:
            return
            
        for prompt in prompts:
            if prompt.prompt_id == prompt_id:
                prompt.status = status
                break
                
        self._save_prompt_plan(task_id, prompts)
        logger.info(f"Updated prompt {prompt_id} status to {status}")
    
    def get_prompt_dependencies(self, prompt_id: str, task_id: str) -> List[str]:
        """Get dependencies for a prompt.
        
        Args:
            prompt_id: ID of the prompt
            task_id: ID of the task
            
        Returns:
            List of dependent prompt IDs
        """
        prompts = self.load_prompt_plan(task_id)
        if not prompts:
            return []
            
        prompt = next((p for p in prompts if p.prompt_id == prompt_id), None)
        return prompt.dependencies if prompt else [] 