import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from dreamforge.agents.workflow_agent import WorkflowAgent
from dreamforge.core.coordination.agent_bus import AgentBus
from dreamforge.core.feedback_engine import FeedbackEngine
from dreamforge.core.prompt_staging_service import PromptStagingService

# --- Test Fixtures ---

@pytest.fixture
def mock_agent_bus():
    bus = Mock(spec=AgentBus)
    bus.send_message.return_value = True
    bus.list_agents.return_value = ["PlannerAgent", "CalendarAgent", "SocialAgent"]
    return bus

@pytest.fixture
def mock_feedback_engine():
    engine = Mock(spec=FeedbackEngine)
    engine.process_feedback.return_value = True
    return engine

@pytest.fixture
def mock_prompt_staging():
    staging = Mock(spec=PromptStagingService)
    staging.update_prompt.return_value = True
    return staging

@pytest.fixture
def workflow_agent(mock_agent_bus, mock_feedback_engine, mock_prompt_staging):
    agent = WorkflowAgent(mock_agent_bus)
    agent.feedback_engine = mock_feedback_engine
    agent.prompt_staging = mock_prompt_staging
    
    # Set up test capabilities
    agent.agent_capabilities = {
        "PlannerAgent": ["planning", "scheduling"],
        "CalendarAgent": ["calendar", "scheduling"],
        "SocialAgent": ["social", "posting"]
    }
    
    # Reset agent load
    agent.agent_load = {
        "PlannerAgent": 0,
        "CalendarAgent": 0,
        "SocialAgent": 0
    }
    
    return agent

# --- Test Core Method: plan_task() ---

def test_plan_task_capable_agent_selection(workflow_agent):
    """Tests that plan_task correctly selects capable agents based on requirements."""
    task_spec = {
        "task_id": "TASK-001",
        "required_capabilities": ["planning", "scheduling"],
        "priority": "high"
    }
    
    result = workflow_agent.plan_task(task_spec)
    
    assert result["task_id"] == "TASK-001"
    assert result["assigned_agent"] == "PlannerAgent"  # Should select PlannerAgent as it has both capabilities
    assert len(result["fallback_agents"]) == 1  # CalendarAgent as fallback (has scheduling)
    assert result["priority"] == "high"
    assert isinstance(result["estimated_duration"], float)
    assert isinstance(result["resource_requirements"], dict)

def test_plan_task_no_capable_agents(workflow_agent):
    """Tests error handling when no agents have required capabilities."""
    task_spec = {
        "task_id": "TASK-002",
        "required_capabilities": ["unknown_capability"],
        "priority": "medium"
    }
    
    with pytest.raises(ValueError) as exc_info:
        workflow_agent.plan_task(task_spec)
    assert "No agents found with required capabilities" in str(exc_info.value)

def test_plan_task_load_balancing(workflow_agent):
    """Tests that plan_task considers agent load when selecting primary agent."""
    # Set up different agent loads
    workflow_agent.agent_load["PlannerAgent"] = 2
    workflow_agent.agent_load["CalendarAgent"] = 0
    
    task_spec = {
        "task_id": "TASK-003",
        "required_capabilities": ["scheduling"],
        "priority": "medium"
    }
    
    result = workflow_agent.plan_task(task_spec)
    assert result["assigned_agent"] == "CalendarAgent"  # Should pick less loaded agent
    assert "PlannerAgent" in result["fallback_agents"]

# --- Test Core Method: assign_agent() ---

def test_assign_agent_success(workflow_agent, mock_agent_bus):
    """Tests successful task assignment to primary agent."""
    planned_execution = {
        "task_id": "TASK-001",
        "assigned_agent": "PlannerAgent",
        "fallback_agents": ["CalendarAgent"],
        "estimated_duration": 60.0,
        "priority": "high"
    }
    
    success = workflow_agent.assign_agent("TASK-001", planned_execution)
    
    assert success is True
    mock_agent_bus.send_message.assert_called_once()
    assert workflow_agent.agent_load["PlannerAgent"] == 1

def test_assign_agent_fallback(workflow_agent, mock_agent_bus):
    """Tests fallback agent assignment when primary agent fails."""
    mock_agent_bus.send_message.side_effect = [False, True]  # Primary fails, fallback succeeds
    
    planned_execution = {
        "task_id": "TASK-001",
        "assigned_agent": "PlannerAgent",
        "fallback_agents": ["CalendarAgent"],
        "estimated_duration": 60.0,
        "priority": "high"
    }
    
    success = workflow_agent.assign_agent("TASK-001", planned_execution)
    
    assert success is True
    assert mock_agent_bus.send_message.call_count == 2
    assert workflow_agent.agent_load["CalendarAgent"] == 1
    assert workflow_agent.agent_load["PlannerAgent"] == 0

def test_assign_agent_all_fail(workflow_agent, mock_agent_bus):
    """Tests handling when all agents (primary and fallbacks) fail."""
    mock_agent_bus.send_message.return_value = False
    
    planned_execution = {
        "task_id": "TASK-001",
        "assigned_agent": "PlannerAgent",
        "fallback_agents": ["CalendarAgent"],
        "estimated_duration": 60.0,
        "priority": "high"
    }
    
    success = workflow_agent.assign_agent("TASK-001", planned_execution)
    
    assert success is False
    assert mock_agent_bus.send_message.call_count >= 2
    assert all(load == 0 for load in workflow_agent.agent_load.values())

# --- Test Core Method: check_status() ---

def test_check_status_metrics_format(workflow_agent):
    """Tests that check_status returns correctly formatted metrics."""
    # Set up test task status
    workflow_agent.task_status["TASK-001"] = "in_progress"
    workflow_agent.current_workflow = [
        {"task_id": "TASK-001", "assigned_to": "PlannerAgent", "dependencies": []}
    ]
    
    status, metrics = workflow_agent.check_status("TASK-001")
    
    assert status == "in_progress"
    assert isinstance(metrics, dict)
    assert all(key in metrics for key in [
        "status", "last_update", "duration", "assigned_agent",
        "dependencies_met", "error_count"
    ])
    assert isinstance(metrics["last_update"], str)  # ISO format timestamp

def test_check_status_unknown_task(workflow_agent):
    """Tests check_status behavior for unknown task ID."""
    status, metrics = workflow_agent.check_status("UNKNOWN-TASK")
    
    assert status == "unknown"
    assert metrics == {}

# --- Test Core Method: route_feedback() ---

def test_route_feedback_success_case(workflow_agent, mock_feedback_engine):
    """Tests successful feedback routing and processing."""
    feedback_data = {
        "success": True,
        "type": "task_completion",
        "output": {"result": "Task completed successfully"},
        "metrics": {"duration": 45.2}
    }
    
    success = workflow_agent.route_feedback("TASK-001", feedback_data)
    
    assert success is True
    mock_feedback_engine.process_feedback.assert_called_once()
    assert workflow_agent.task_status.get("TASK-001") == "completed"

def test_route_feedback_failure_and_retry(workflow_agent):
    """Tests feedback routing with failure that triggers retry."""
    feedback_data = {
        "success": False,
        "type": "task_error",
        "errors": [{"code": "TEMP_ERROR", "message": "Temporary failure"}],
        "metrics": {"attempt": 1}
    }
    
    # Mock _should_retry to return True
    workflow_agent._should_retry = Mock(return_value=True)
    workflow_agent._retry_task = Mock()
    
    success = workflow_agent.route_feedback("TASK-001", feedback_data)
    
    assert success is True
    workflow_agent._retry_task.assert_called_once_with("TASK-001")

def test_route_feedback_prompt_update(workflow_agent, mock_prompt_staging):
    """Tests feedback routing that triggers prompt updates."""
    feedback_data = {
        "success": True,
        "type": "task_completion",
        "requires_prompt_update": True,
        "output": {"result": "Task completed with suggestions"}
    }
    
    success = workflow_agent.route_feedback("TASK-001", feedback_data)
    
    assert success is True
    mock_prompt_staging.update_prompt.assert_called_once()

# --- Test Helper Methods ---

def test_find_capable_agents(workflow_agent):
    """Tests helper method for finding agents with required capabilities."""
    agents = workflow_agent._find_capable_agents(["scheduling"])
    assert len(agents) == 2
    assert "PlannerAgent" in agents
    assert "CalendarAgent" in agents

def test_select_optimal_agent(workflow_agent):
    """Tests helper method for selecting agent based on load."""
    workflow_agent.agent_load = {
        "PlannerAgent": 2,
        "CalendarAgent": 1,
        "SocialAgent": 0
    }
    
    optimal = workflow_agent._select_optimal_agent(["PlannerAgent", "CalendarAgent"])
    assert optimal == "CalendarAgent"  # Should select less loaded agent

# --- Test Integration Scenarios ---

def test_full_task_lifecycle(workflow_agent, mock_agent_bus, mock_feedback_engine):
    """Tests complete task lifecycle from planning to completion."""
    # 1. Plan task
    task_spec = {
        "task_id": "TASK-001",
        "required_capabilities": ["planning"],
        "priority": "high"
    }
    planned = workflow_agent.plan_task(task_spec)
    
    # 2. Assign task
    assigned = workflow_agent.assign_agent("TASK-001", planned)
    assert assigned is True
    
    # 3. Check initial status
    status, _ = workflow_agent.check_status("TASK-001")
    assert status != "unknown"
    
    # 4. Route completion feedback
    feedback = {
        "success": True,
        "type": "task_completion",
        "output": {"result": "Success"}
    }
    feedback_routed = workflow_agent.route_feedback("TASK-001", feedback)
    assert feedback_routed is True
    
    # Verify final state
    final_status, metrics = workflow_agent.check_status("TASK-001")
    assert final_status == "completed" 