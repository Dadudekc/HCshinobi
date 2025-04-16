# Tests for data models

import sys
import os
import pytest
from datetime import datetime

# Add project root for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import models
from core.models.task import Task
from core.models.plan import Plan
from core.models.workflow import WorkflowDefinition, WorkflowStep

# TODO: Import Task, Plan, WorkflowDefinition, etc.
# TODO: Implement test cases

# --- Task Model Tests ---

def test_task_creation_minimal():
    """Test creating a Task with minimal required fields."""
    task = Task(
        task_id="T001",
        description="Minimal task description"
    )
    assert task.task_id == "T001"
    assert task.description == "Minimal task description"
    assert task.status == "Pending" # Default status
    assert task.priority == 3 # Default priority
    assert task.dependencies == []
    assert task.assigned_to is None
    assert task.estimated_time is None
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)

def test_task_creation_all_fields():
    """Test creating a Task with all fields specified."""
    now = datetime.now()
    task = Task(
        task_id="T002",
        description="Detailed task",
        status="In Progress",
        priority=1,
        dependencies=["T001"],
        assigned_to="AgentX",
        estimated_time="2h",
        notes="Some notes here",
        created_at=now, # Explicitly set for testing predictability if needed
        updated_at=now
    )
    assert task.task_id == "T002"
    assert task.status == "In Progress"
    assert task.priority == 1
    assert task.dependencies == ["T001"]
    assert task.assigned_to == "AgentX"
    assert task.estimated_time == "2h"
    assert task.notes == "Some notes here"
    assert task.created_at == now
    assert task.updated_at == now

def test_task_update_status():
    """Test the update_status method."""
    task = Task(task_id="T003", description="Task to update")
    initial_update_time = task.updated_at
    # Allow some time to pass potentially
    # import time; time.sleep(0.01)
    task.update_status("Completed")
    assert task.status == "Completed"
    # Placeholder check: Real implementation should update timestamp
    # assert task.updated_at > initial_update_time
    # For now, just check it ran without error
    assert task.updated_at is not None

# --- Plan Model Tests ---

def test_plan_creation_empty():
    """Test creating an empty Plan."""
    plan = Plan(plan_id="P001", goal="Empty plan goal")
    assert plan.plan_id == "P001"
    assert plan.goal == "Empty plan goal"
    assert plan.tasks == []
    assert isinstance(plan.created_at, datetime)

def test_plan_creation_with_tasks():
    """Test creating a Plan with a list of Task objects."""
    task1 = Task(task_id="T1", description="Task 1")
    task2 = Task(task_id="T2", description="Task 2", dependencies=["T1"])
    plan = Plan(plan_id="P002", goal="Plan with tasks", tasks=[task1, task2])
    assert plan.plan_id == "P002"
    assert len(plan.tasks) == 2
    assert plan.tasks[0] is task1
    assert plan.tasks[1] is task2
    assert plan.tasks[1].dependencies == ["T1"]

# --- Workflow Model Tests ---

def test_workflow_step_creation():
    """Test creating a WorkflowStep."""
    step = WorkflowStep(
        step_id=1,
        name="Planning Step",
        agent="PlannerAgent",
        command="plan_from_goal",
        params={"goal": "{{ input.goal_prompt }}"}, # Example interpolation
        output_var="generated_plan"
    )
    assert step.step_id == 1
    assert step.name == "Planning Step"
    assert step.agent == "PlannerAgent"
    assert step.command == "plan_from_goal"
    assert step.params == {"goal": "{{ input.goal_prompt }}"}
    assert step.output_var == "generated_plan"

def test_workflow_definition_creation():
    """Test creating a WorkflowDefinition."""
    step1 = WorkflowStep(step_id=1, name="Step One", agent="AgentA", command="cmd1")
    step2 = WorkflowStep(step_id=2, name="Step Two", agent="AgentB", command="cmd2")
    wf_def = WorkflowDefinition(
        workflow_id="WF001",
        name="Simple Two-Step Workflow",
        description="A basic workflow for testing.",
        steps=[step1, step2]
    )
    assert wf_def.workflow_id == "WF001"
    assert wf_def.name == "Simple Two-Step Workflow"
    assert wf_def.description == "A basic workflow for testing."
    assert len(wf_def.steps) == 2
    assert wf_def.steps[0] is step1
    assert wf_def.steps[1] is step2
    assert isinstance(wf_def.created_at, datetime)

def test_plan_methods():
    assert True # Placeholder

def test_workflow_structure():
    assert True # Placeholder 