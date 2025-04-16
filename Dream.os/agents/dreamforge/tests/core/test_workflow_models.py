"""Tests for workflow models."""
import pytest
from datetime import datetime
from dreamforge.core.models.workflow import WorkflowStep, WorkflowDefinition

def test_workflow_step_initialization():
    """Test WorkflowStep initialization."""
    step = WorkflowStep("step1", "Test step", ["dep1", "dep2"])
    
    assert step.step_id == "step1"
    assert step.description == "Test step"
    assert step.dependencies == ["dep1", "dep2"]
    assert step.status == "pending"
    assert step.result is None
    assert step.started_at is None
    assert step.completed_at is None

def test_workflow_step_lifecycle():
    """Test WorkflowStep lifecycle state changes."""
    step = WorkflowStep("step1", "Test step")
    
    # Test start
    step.start()
    assert step.status == "running"
    assert step.started_at is not None
    
    # Test completion
    result = {"output": "test"}
    step.complete(result)
    assert step.status == "completed"
    assert step.result == result
    assert step.completed_at is not None
    
    # Test failure
    step = WorkflowStep("step2", "Failed step")
    error = "Test error"
    step.fail(error)
    assert step.status == "failed"
    assert step.result == {"error": error}
    assert step.completed_at is not None

def test_workflow_step_serialization():
    """Test WorkflowStep serialization."""
    step = WorkflowStep("step1", "Test step", ["dep1"])
    step.start()
    step.complete({"output": "test"})
    
    # Test to_dict
    step_dict = step.to_dict()
    assert step_dict["id"] == "step1"
    assert step_dict["description"] == "Test step"
    assert step_dict["dependencies"] == ["dep1"]
    assert step_dict["status"] == "completed"
    assert step_dict["result"] == {"output": "test"}
    assert step_dict["started_at"] is not None
    assert step_dict["completed_at"] is not None
    
    # Test from_dict
    new_step = WorkflowStep.from_dict(step_dict)
    assert new_step.step_id == step.step_id
    assert new_step.description == step.description
    assert new_step.dependencies == step.dependencies
    assert new_step.status == step.status
    assert new_step.result == step.result
    assert new_step.started_at == step.started_at
    assert new_step.completed_at == step.completed_at

def test_workflow_definition_initialization():
    """Test WorkflowDefinition initialization."""
    workflow = WorkflowDefinition("wf1", "Test Workflow", "A test workflow")
    
    assert workflow.workflow_id == "wf1"
    assert workflow.name == "Test Workflow"
    assert workflow.description == "A test workflow"
    assert workflow.steps == {}
    assert workflow.status == "pending"
    assert workflow.created_at is not None
    assert workflow.updated_at is None

def test_workflow_definition_step_management():
    """Test WorkflowDefinition step management."""
    workflow = WorkflowDefinition("wf1", "Test Workflow", "A test workflow")
    step1 = WorkflowStep("step1", "First step")
    step2 = WorkflowStep("step2", "Second step", ["step1"])
    
    # Test adding steps
    workflow.add_step(step1)
    workflow.add_step(step2)
    assert len(workflow.steps) == 2
    assert workflow.get_step("step1") == step1
    assert workflow.get_step("step2") == step2
    
    # Test updating steps
    workflow.update_step("step1", "running")
    assert workflow.get_step("step1").status == "running"
    assert workflow.status == "running"
    
    workflow.update_step("step1", "completed", {"output": "test"})
    assert workflow.get_step("step1").status == "completed"
    assert workflow.get_step("step1").result == {"output": "test"}
    
    workflow.update_step("step2", "failed", "Error message")
    assert workflow.get_step("step2").status == "failed"
    assert workflow.status == "failed"

def test_workflow_definition_status_updates():
    """Test WorkflowDefinition status updates."""
    workflow = WorkflowDefinition("wf1", "Test Workflow", "A test workflow")
    
    # Empty workflow should be pending
    assert workflow.status == "pending"
    
    # Add a step and start it
    step = WorkflowStep("step1", "Test step")
    workflow.add_step(step)
    workflow.update_step("step1", "running")
    assert workflow.status == "running"
    
    # Complete the step
    workflow.update_step("step1", "completed")
    assert workflow.status == "completed"
    
    # Add another step
    step2 = WorkflowStep("step2", "Second step")
    workflow.add_step(step2)
    assert workflow.status == "pending"  # Not all steps are completed
    
    # Fail the second step
    workflow.update_step("step2", "failed", "Error")
    assert workflow.status == "failed"

def test_workflow_definition_serialization():
    """Test WorkflowDefinition serialization."""
    workflow = WorkflowDefinition("wf1", "Test Workflow", "A test workflow")
    step = WorkflowStep("step1", "Test step")
    workflow.add_step(step)
    workflow.update_step("step1", "completed", {"output": "test"})
    
    # Test to_dict
    workflow_dict = workflow.to_dict()
    assert workflow_dict["id"] == "wf1"
    assert workflow_dict["name"] == "Test Workflow"
    assert workflow_dict["description"] == "A test workflow"
    assert workflow_dict["status"] == "completed"
    assert len(workflow_dict["steps"]) == 1
    assert workflow_dict["created_at"] is not None
    assert workflow_dict["updated_at"] is not None
    
    # Test from_dict
    new_workflow = WorkflowDefinition.from_dict(workflow_dict)
    assert new_workflow.workflow_id == workflow.workflow_id
    assert new_workflow.name == workflow.name
    assert new_workflow.description == workflow.description
    assert new_workflow.status == workflow.status
    assert len(new_workflow.steps) == len(workflow.steps)
    assert new_workflow.created_at == workflow.created_at
    assert new_workflow.updated_at == workflow.updated_at
    
    # Verify step was properly deserialized
    new_step = new_workflow.get_step("step1")
    assert new_step is not None
    assert new_step.status == "completed"
 