import sys
import os
from dataclasses import dataclass, field
from typing import List, Optional
from .task import Task, TaskStatus # Import Task and TaskStatus
import uuid
from datetime import datetime, timezone
import re # For parsing estimated time

# Add project root for imports if needed (for log_event)
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import logger (handle potential import error for standalone use)
try:
    from core.governance_memory_engine import log_event
except ImportError:
    print(f"[PlanModel] Warning: Real log_event not imported. Using dummy.")
    def log_event(etype, src, dtls): print(f"[LOG] {etype} | {src} | {dtls}")


@dataclass
class Plan:
    """Represents a collection of tasks designed to achieve a specific goal.

    Attributes:
        plan_id (str): A unique identifier for the plan.
        goal (Optional[str]): The high-level goal this plan aims to achieve.
        tasks (List[Task]): A list of Task objects comprising the plan.
        created_at (datetime): Timestamp (UTC) when the plan object was created.
        status (str): Overall status of the plan (e.g., "Active", "Completed", "Aborted").
                     Consider using an Enum for more robust status management in the future.
    """
    plan_id: str = field(default_factory=lambda: f"P-{uuid.uuid4()}")
    goal: Optional[str] = None
    tasks: List[Task] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "Active"

    def __post_init__(self):
        """Validate plan attributes after initialization."""
        if self.goal is not None and not isinstance(self.goal, str):
            raise TypeError("Plan goal must be a string or None.")
            
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)

        # Validate tasks list contains Task instances
        if not isinstance(self.tasks, list):
             raise TypeError(f"Plan tasks must be a list (got {type(self.tasks)})")
             
        validated_tasks = []
        for i, task_data in enumerate(self.tasks):
            if isinstance(task_data, Task):
                validated_tasks.append(task_data)
            elif isinstance(task_data, dict):
                try:
                    # Attempt to coerce dict to Task (requires Task model to handle dict init)
                    # This assumes Task.__init__ or a factory can handle dicts.
                    # If Task only uses @dataclass defaults, this might need more work.
                    # For now, we rely on the Task refinement (DF-MODEL-001) implicitly.
                    task = Task(**task_data)
                    log_event("MODEL_INFO", "Plan", {"plan_id": self.plan_id, "info": f"Coerced task {i} from dict to Task."})
                    validated_tasks.append(task)
                except Exception as e:
                    raise TypeError(f"Error coercing task {i} from dict: {e}")
            else:
                 raise TypeError(f"Task {i} must be a Task object or dictionary, not {type(task_data)}")
        self.tasks = validated_tasks # Replace with validated/coerced list

    def add_task(self, task: Task):
        """Adds a Task object to the plan's task list.

        Args:
            task (Task): The Task object to add.
        
        Raises:
            TypeError: If the provided item is not a Task instance.
        """
        if not isinstance(task, Task):
            raise TypeError("Only Task objects can be added to the plan.")
        self.tasks.append(task)
        log_event("PLAN_TASK_ADDED", "Plan", {"plan_id": self.plan_id, "added_task_id": task.task_id})

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Retrieves a task from the plan by its ID.

        Args:
            task_id (str): The unique ID of the task to find.

        Returns:
            Optional[Task]: The found Task object, or None if not found.
        """
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Retrieves all tasks within the plan matching the given status.

        Args:
            status (TaskStatus): The TaskStatus enum member to filter by.

        Returns:
            List[Task]: A list of tasks matching the status.
        """
        if not isinstance(status, TaskStatus):
             log_event("MODEL_WARNING", "Plan", {"plan_id": self.plan_id, "warning": f"Invalid status type '{type(status)}' passed to get_tasks_by_status. Expected TaskStatus Enum."})
             return []
        return [task for task in self.tasks if task.status == status]
        
    def calculate_total_estimated_time(self) -> (Optional[float], str):
        """Calculates the total estimated time for all tasks in hours.

        Parses 'estimated_time' strings (e.g., "2h", "30m", "1.5h"). Tasks with
        unparseable estimates are skipped and logged.

        Returns:
            Tuple[Optional[float], str]: A tuple containing the total estimated hours (float)
                                         or None if no tasks have estimates, and a status message.
        """
        total_hours = 0.0
        tasks_with_estimates = 0
        parse_errors = 0
        status_message = ""

        for task in self.tasks:
            if task.estimated_time:
                try:
                    match = re.match(r"\s*(\d*\.?\d+)\s*([hm])\s*", task.estimated_time, re.IGNORECASE)
                    if match:
                        value = float(match.group(1))
                        unit = match.group(2).lower()
                        if unit == 'h':
                            total_hours += value
                        elif unit == 'm':
                            total_hours += value / 60.0
                        tasks_with_estimates += 1
                    else:
                        raise ValueError("Unknown format")
                except (ValueError, TypeError) as e:
                    parse_errors += 1
                    log_event("MODEL_WARNING", "Plan", {
                        "plan_id": self.plan_id,
                        "task_id": task.task_id,
                        "warning": f"Could not parse estimated_time '{task.estimated_time}': {e}"
                    })
            
        if tasks_with_estimates == 0 and parse_errors == 0:
            status_message = "No tasks with estimated time found."
            log_event("PLAN_INFO", "Plan", {"plan_id": self.plan_id, "message": status_message})
            return None, status_message
        elif parse_errors > 0:
            status_message = f"Calculated based on {tasks_with_estimates} tasks. Skipped {parse_errors} tasks due to unparseable estimates."
            log_event("PLAN_WARNING", "Plan", {"plan_id": self.plan_id, "message": status_message})
        else:
            status_message = f"Total estimated time for {tasks_with_estimates} tasks calculated successfully."
            log_event("PLAN_INFO", "Plan", {"plan_id": self.plan_id, "total_hours": total_hours, "message": status_message})
            
        return total_hours, status_message

    def reorder_tasks(self, new_order: List[str]):
        """Placeholder for reordering tasks. 
        
        Note: True reordering should consider dependencies. This is a basic list reorder.
        Logs a warning about the simplistic nature.
        
        Args:
            new_order (List[str]): A list of task_ids in the desired new order.
        """
        log_event("MODEL_WARNING", "Plan", {"plan_id": self.plan_id, "warning": "reorder_tasks called - basic implementation ignores dependencies."})
        # Basic implementation - Creates a new list based on the order provided.
        # Tasks not in new_order will be lost unless handled differently.
        ordered_tasks = []
        task_map = {task.task_id: task for task in self.tasks}
        present_ids = set()
        for task_id in new_order:
            if task_id in task_map:
                ordered_tasks.append(task_map[task_id])
                present_ids.add(task_id)
            else:
                 log_event("MODEL_WARNING", "Plan", {"plan_id": self.plan_id, "warning": f"Task ID '{task_id}' in new_order not found in plan."})
        
        # Optionally add back tasks that were in the plan but not in new_order
        # for task_id, task in task_map.items():
        #     if task_id not in present_ids:
        #         ordered_tasks.append(task)
                
        self.tasks = ordered_tasks
        log_event("PLAN_TASKS_REORDERED", "Plan", {"plan_id": self.plan_id, "new_order_ids": new_order})


# Example Usage:
if __name__ == '__main__':
    # Uses refined Task from sibling module
    from .task import Task, TaskStatus

    try:
        plan1 = Plan(goal="Launch new product")
        print(f"Plan 1 Created: ID={plan1.plan_id}, Goal={plan1.goal}, Created={plan1.created_at.isoformat()}")

        task_a = Task(description="Market research", priority=1, estimated_time=" 4 h ")
        task_b = Task(description="Develop prototype", dependencies=[task_a.task_id], priority=1, estimated_time="120m")
        task_c = Task(description="User testing", dependencies=[task_b.task_id], priority=2, estimated_time="1.5h")
        task_d = Task(description="Documentation", dependencies=[task_b.task_id], priority=3, estimated_time="bad estimate") # Bad estimate
        task_e = Task(description="Deployment", dependencies=[task_c.task_id, task_d.task_id]) # No estimate

        plan1.add_task(task_a)
        plan1.add_task(task_b)
        plan1.add_task(task_c)
        plan1.add_task(task_d)
        plan1.add_task(task_e)
        
        print(f"\nPlan Tasks ({len(plan1.tasks)}): {[t.task_id for t in plan1.tasks]}")

        print("\nFinding task B:")
        found_task = plan1.get_task_by_id(task_b.task_id)
        if found_task: print(f"  Found: {found_task.description}")

        print("\nUpdating status of task B:")
        if found_task:
            found_task.update_status(TaskStatus.COMPLETED)

        print("\nFinding PENDING tasks:")
        pending = plan1.get_tasks_by_status(TaskStatus.PENDING)
        print(f"  Found {len(pending)} Pending: {[t.task_id for t in pending]}")

        print("\nCalculating estimated time...")
        total_time, msg = plan1.calculate_total_estimated_time()
        print(f"  Result: {total_time} hours")
        print(f"  Message: {msg}")
        
        print("\nReordering tasks (simplistic)...")
        new_order = [task_e.task_id, task_c.task_id, task_a.task_id, task_b.task_id, "MISSING_ID"]
        plan1.reorder_tasks(new_order)
        print(f"  New Task Order: {[t.task_id for t in plan1.tasks]}")

    except (ValueError, TypeError) as ve:
        print(f"\nCaught Validation Error: {ve}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}") 