from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from core.todo_manager import FullSyncTodoManager
from .types import TodoItem
from .prompt_builder import PromptBuilder

class PromptTodoInjector:
    """
    Injects TODO tasks into the prompt cycle system.
    Integrates with FullSyncTodoManager to convert TODOs into prompt tasks using PromptBuilder.
    """
    
    def __init__(self, project_root: str, config: Optional[Dict] = None):
        self.project_root = project_root
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize todo manager
        self.todo_manager = FullSyncTodoManager(project_root, config)
        
        # Configuration
        self.prompt_template = self.config.get(
            "prompt_template",
            "cursor_prompts/full_sync_mode/todo_prompt.jinja"
        )
        self.min_priority = self.config.get("min_priority", "Medium")
        self.exclude_categories = self.config.get("exclude_categories", [])
        
    def inject_todo_prompts(self, cycle_context: Dict) -> Dict:
        """
        Injects TODO tasks into the prompt cycle context.
        
        Args:
            cycle_context: The current prompt cycle context
            
        Returns:
            Updated cycle context with injected TODO prompts
        """
        # Scan for TODOs if not already done
        if not self.todo_manager.tasks:
            self.logger.info("No tasks loaded, scanning codebase...")
            self.todo_manager.scan_codebase()
            self.logger.info(f"Scan complete. Found {len(self.todo_manager.tasks)} tasks initially.")
            
        # Get active tasks that meet our criteria
        eligible_tasks = self._get_eligible_tasks()
        self.logger.info(f"Found {len(eligible_tasks)} eligible tasks for prompt injection.")
        
        # Convert tasks to prompts using PromptBuilder
        prompts = []
        for task in eligible_tasks:
            # Cast task dict to TodoItem for type checking if needed, though static analysis handles it
            prompt = PromptBuilder.build_prompt_preview(
                todo=task, # Pass the task dictionary directly
                project_root=self.project_root,
                template=self.prompt_template
            )
            if prompt:
                prompts.append(prompt)
                
        self.logger.info(f"Generated {len(prompts)} prompts from eligible tasks.")
        
        # Add prompts to cycle context
        if "prompts" not in cycle_context:
            cycle_context["prompts"] = []
        cycle_context["prompts"].extend(prompts)
        
        return cycle_context
        
    def _get_eligible_tasks(self) -> List[TodoItem]: # Return list of TodoItem
        """
        Gets tasks that are eligible for prompt injection based on status, priority, category, and dependencies.
        
        Returns:
            List of eligible TodoItem tasks.
        """
        # Get active tasks
        tasks = self.todo_manager.get_active_tasks() # This should return List[Dict]
        
        # Filter by priority
        priority_order = {"High": 3, "Medium": 2, "Low": 1}
        min_priority_level = priority_order.get(self.min_priority, 2)
        
        eligible_tasks: List[TodoItem] = [] # Ensure list holds TodoItem type
        for task_dict in tasks:
            # Basic check if task_dict is structured as expected before treating as TodoItem
            if not isinstance(task_dict, dict) or "priority" not in task_dict or "category" not in task_dict:
                 self.logger.warning(f"Skipping malformed task data: {task_dict.get('task_id', 'Unknown ID')}")
                 continue

            task: TodoItem = task_dict # Treat as TodoItem after basic validation
            
            # Skip excluded categories
            if task.get("category") in self.exclude_categories:
                continue
                
            # Check priority
            task_priority = task.get("priority", "Low")
            if priority_order.get(task_priority, 1) < min_priority_level:
                continue
                
            # Check dependencies
            dependencies = task.get("dependencies")
            if dependencies:
                if not self._are_dependencies_met(dependencies):
                    continue
                    
            eligible_tasks.append(task)
            
        return eligible_tasks
        
    def _are_dependencies_met(self, dependencies: List[str]) -> bool:
        """
        Checks if all task dependencies are met (status is 'Completed').
        
        Args:
            dependencies: List of task IDs that are dependencies.
            
        Returns:
            True if all dependencies are met, False otherwise.
        """
        for dep_id in dependencies:
            dep_task = self.todo_manager.get_task(dep_id)
            if not dep_task or dep_task.get("status") != "Completed":
                return False
        return True
        
    # Removed _create_prompt_from_task method as logic is moved to PromptBuilder 