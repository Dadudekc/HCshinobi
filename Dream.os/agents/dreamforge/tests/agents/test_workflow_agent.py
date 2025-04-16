"""Tests for WorkflowAgent."""
import os
import pytest
from unittest.mock import patch, AsyncMock
import json

from dreamforge.tests.core.utils.test_utils import (
    setup_test_imports,
    init_test_suite,
    mock_agent_bus,
    temp_workspace,
    cleanup_test_env,
    check_system_health
)

setup_test_imports()

from dreamforge.agents.workflow_agent import WorkflowAgent, AGENT_ID, WORKFLOW_STORAGE_DIR
from core.models.workflow import WorkflowDefinition, WorkflowStep
from dreamforge.tests.core.utils.llm_test_utils import LLMTestResponse, patch_llm_chain
from dreamforge.core.memory.governance_memory_engine import log_event

# --- Test Data ---

@pytest.fixture(autouse=True)
def _setup_and_cleanup(cleanup_test_env):
    """Ensure test environment is clean before and after tests."""
    yield

@pytest.fixture
def workflow_agent_instance(mock_agent_bus, temp_workspace):
    """Provides a WorkflowAgent instance with mocked AgentBus and temp workflow dir."""
    workflow_dir = os.path.join(temp_workspace, "workflows")
    os.makedirs(workflow_dir)
    
    with patch('dreamforge.agents.workflow_agent.AgentBus') as MockAgentBus, \
         patch('dreamforge.agents.workflow_agent.WORKFLOW_STORAGE_DIR', workflow_dir):
        MockAgentBus.return_value = mock_agent_bus
        agent = WorkflowAgent()
        yield agent, mock_agent_bus, workflow_dir

@pytest.fixture
def sample_workflow_dict():
    """Sample workflow data for testing."""
    return {
        "workflow_id": "test-workflow-123",
        "name": "Test Workflow",
        "description": "A test workflow for unit testing",
        "steps": [
            {
                "step_id": "step1",
                "name": "First Step",
                "description": "Initial step",
                "agent": "test_agent",
                "command": "test_command",
                "dependencies": []
            },
            {
                "step_id": "step2",
                "name": "Second Step",
                "description": "Final step",
                "agent": "test_agent",
                "command": "test_command",
                "dependencies": ["step1"]
            }
        ]
    }

class TestWorkflowGeneration:
    """Tests for workflow generation functionality."""

    @patch_llm_chain("dreamforge.agents.workflow_agent")
    def test_generate_workflow_success(self, llm_chain, workflow_agent_instance, sample_workflow_dict):
        """Test successful workflow generation and saving."""
        agent, _, workflow_dir = workflow_agent_instance
        llm_chain.setup_response(LLMTestResponse.with_json(sample_workflow_dict))
        prompt = "Create a plan and schedule it."
        
        result = agent.generate_workflow(prompt)
        
        assert result["status"] == "success"
        assert "workflow" in result
        assert result["workflow"]["workflow_id"] == sample_workflow_dict["workflow_id"]
        assert result["workflow"]["name"] == sample_workflow_dict["name"]
        assert len(result["workflow"]["steps"]) == 2
        
        llm_chain.verify_call(
            "agents/prompts/workflow/generate_workflow.j2",
            {"user_prompt": prompt},
            AGENT_ID,
            "generate_workflow"
        )
        
        # Check if file was saved correctly
        expected_save_path = os.path.join(workflow_dir, f"{sample_workflow_dict['workflow_id']}.json")
        with open(expected_save_path, 'r', encoding='utf-8') as f:
            saved_data = json.loads(f.read())
            assert saved_data['workflow_id'] == sample_workflow_dict['workflow_id']
            assert 'created_at' in saved_data

    @patch_llm_chain("dreamforge.agents.workflow_agent")
    def test_generate_workflow_llm_fails(self, llm_chain, workflow_agent_instance):
        """Test generate_workflow when LLM call fails."""
        agent, _, _ = workflow_agent_instance
        llm_chain.setup_response(LLMTestResponse.with_error(), should_fail=True)
        
        result = agent.generate_workflow("test")
        assert result["status"] == "error"
        assert "LLM execution failed" in result["details"]

    @patch_llm_chain("dreamforge.agents.workflow_agent")
    def test_generate_workflow_parsing_fails(self, llm_chain, workflow_agent_instance):
        """Test generate_workflow when LLM response parsing fails."""
        agent, _, _ = workflow_agent_instance
        llm_chain.setup_response(LLMTestResponse.with_error("invalid_json"))
        
        result = agent.generate_workflow("test")
        assert result["status"] == "error"
        assert "Failed to parse workflow" in result["details"]

    @patch_llm_chain("dreamforge.agents.workflow_agent")
    def test_generate_workflow_save_fails(self, llm_chain, workflow_agent_instance, sample_workflow_dict):
        """Test generate_workflow when saving the file fails."""
        agent, _, _ = workflow_agent_instance
        llm_chain.setup_response(LLMTestResponse.with_json(sample_workflow_dict))
        
        with patch('dreamforge.agents.workflow_agent.open', side_effect=IOError("Disk full")):
            result = agent.generate_workflow("test")
            assert result["status"] == "error"
            assert "Failed to save generated workflow" in result["details"]

class TestWorkflowExecution:
    """Tests for workflow execution functionality."""

    @patch_llm_chain("dreamforge.agents.workflow_agent")
    def test_execute_workflow_success(self, llm_chain, workflow_agent_instance, sample_workflow_dict):
        """Test successful workflow execution."""
        agent, mock_bus, _ = workflow_agent_instance
        workflow = WorkflowDefinition(**sample_workflow_dict)
        
        result = agent.execute_workflow(workflow)
        
        assert result["status"] == "success"
        assert len(result["step_results"]) == 2
        assert all(step["status"] == "success" for step in result["step_results"])
        
        # Verify bus dispatches
        assert mock_bus.dispatch.call_count == 2
        mock_bus.dispatch.assert_any_call("test_agent", "test_command")

    @patch_llm_chain("dreamforge.agents.workflow_agent")
    def test_execute_workflow_step_fails(self, llm_chain, workflow_agent_instance, sample_workflow_dict):
        """Test workflow execution when a step fails."""
        agent, mock_bus, _ = workflow_agent_instance
        mock_bus.dispatch.side_effect = Exception("Step failed")
        workflow = WorkflowDefinition(**sample_workflow_dict)
        
        result = agent.execute_workflow(workflow)
        
        assert result["status"] == "error"
        assert "Failed to execute step" in result["details"]
        assert len(result["step_results"]) == 1  # Only first step attempted
        assert result["step_results"][0]["status"] == "error"

class TestWorkflowManagement:
    """Tests for workflow management functionality."""

    def test_list_workflows_success(self, workflow_agent_instance, sample_workflow_dict):
        """Test successful listing of workflows."""
        agent, _, workflow_dir = workflow_agent_instance
        
        # Create test workflow files
        for i in range(3):
            workflow = sample_workflow_dict.copy()
            workflow["workflow_id"] = f"test-workflow-{i}"
            path = os.path.join(workflow_dir, f"{workflow['workflow_id']}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(workflow, f)
        
        result = agent.list_workflows()
        
        assert result["status"] == "success"
        assert len(result["workflows"]) == 3
        assert all("workflow_id" in w for w in result["workflows"])

    def test_list_workflows_empty(self, workflow_agent_instance):
        """Test listing workflows when directory is empty."""
        agent, _, _ = workflow_agent_instance
        
        result = agent.list_workflows()
        
        assert result["status"] == "success"
        assert len(result["workflows"]) == 0

    def test_list_workflows_dir_not_found(self, workflow_agent_instance):
        """Test listing workflows when directory doesn't exist."""
        agent, _, workflow_dir = workflow_agent_instance
        os.rmdir(workflow_dir)  # Remove the workflow directory
        
        result = agent.list_workflows()
        
        assert result["status"] == "error"
        assert "Failed to list workflows" in result["details"]

def test_system_health():
    """Verify system health before shutdown."""
    health_results = check_system_health()
    assert health_results["directories"]["status"] == "pass", "Critical directories not accessible"
    assert health_results["agent_files"]["status"] == "pass", "Agent files not properly maintained"
    assert health_results["task_system"]["status"] == "pass", "Task system issues detected"

# Initialize test suite
init_test_suite(
    "TestWorkflowAgent",
    test_count=10,  # Updated count to include health check
    test_categories=["generation", "execution", "management", "health"]
)