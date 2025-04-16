import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
from agents.workflow_agent import WorkflowAgent
from dreamforge.core.governance_memory_engine import log_event

class TestWorkflowAgent(unittest.TestCase):
    def setUp(self):
        self.agent = WorkflowAgent()
        self.test_workflow = {
            "workflow_id": "test_workflow_id",
            "name": "Test Workflow",
            "steps": [
                {
                    "step_id": "step1",
                    "name": "First Step",
                    "action": "test_action",
                    "params": {"param1": "value1"}
                }
            ]
        }
        # Log test initialization
        log_event("TEST_ADDED", "TestWorkflowAgent", {"test_suite": "WorkflowAgent"})

    def tearDown(self):
        """Clean up any test artifacts."""
        # Clean up test workflows if they exist
        if hasattr(self.agent, '_workflows'):
            self.agent._workflows.clear()

    @patch('agents.workflow_agent.log_event')
    def test_create_workflow_success(self, mock_log_event):
        """Test successful workflow creation with event logging."""
        result = self.agent.create_workflow(self.test_workflow)
        self.assertTrue(result)
        mock_log_event.assert_called_with(
            "WORKFLOW_CREATED",
            self.agent.agent_id,
            {"workflow_id": self.test_workflow["workflow_id"]}
        )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_create_workflow_success"})

    @patch('agents.workflow_agent.log_event')
    def test_create_workflow_duplicate(self, mock_log_event):
        """Test creating a workflow with duplicate ID."""
        # Create first workflow
        self.agent.create_workflow(self.test_workflow)
        # Attempt to create duplicate
        result = self.agent.create_workflow(self.test_workflow)
        self.assertFalse(result)
        mock_log_event.assert_called_with(
            "WORKFLOW_CREATION_FAILED",
            self.agent.agent_id,
            {"error": "Workflow ID already exists", "workflow_id": self.test_workflow["workflow_id"]}
        )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_create_workflow_duplicate"})

    @patch('agents.workflow_agent.log_event')
    def test_execute_workflow_step_failure(self, mock_log_event):
        """Test workflow execution with failing step."""
        failing_workflow = {
            "workflow_id": "failing_workflow",
            "name": "Failing Workflow",
            "steps": [
                {
                    "step_id": "fail_step",
                    "name": "Failing Step",
                    "action": "nonexistent_action",
                    "params": {}
                }
            ]
        }
        self.agent.create_workflow(failing_workflow)
        result = self.agent.execute_workflow("failing_workflow")
        self.assertEqual(result["status"], "error")
        self.assertIn("step_error", result)
        mock_log_event.assert_called_with(
            "WORKFLOW_STEP_FAILED",
            self.agent.agent_id,
            {"workflow_id": "failing_workflow", "step_id": "fail_step"}
        )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_execute_workflow_step_failure"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_validation(self, mock_log_event):
        """Test workflow validation with various invalid cases."""
        invalid_cases = [
            ({}, "Missing required fields"),
            ({"workflow_id": "test"}, "Missing steps field"),
            ({"workflow_id": "test", "steps": "not_a_list"}, "Steps must be a list"),
            ({"workflow_id": "test", "steps": [{"invalid": "step"}]}, "Invalid step format")
        ]
        for invalid_workflow, expected_error in invalid_cases:
            result = self.agent.create_workflow(invalid_workflow)
            self.assertFalse(result)
            mock_log_event.assert_called_with(
                "WORKFLOW_VALIDATION_FAILED",
                self.agent.agent_id,
                {"error": expected_error}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_validation"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_persistence_failure(self, mock_log_event):
        """Test workflow persistence with storage failures."""
        with patch.object(self.agent, '_save_workflow', side_effect=Exception("Storage error")):
            result = self.agent.create_workflow(self.test_workflow)
            self.assertFalse(result)
            mock_log_event.assert_called_with(
                "WORKFLOW_STORAGE_ERROR",
                self.agent.agent_id,
                {"error": "Failed to persist workflow", "workflow_id": self.test_workflow["workflow_id"]}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_persistence_failure"})

    @patch('agents.workflow_agent.log_event')
    def test_concurrent_workflow_execution(self, mock_log_event):
        """Test handling of concurrent workflow executions."""
        self.agent.create_workflow(self.test_workflow)
        with patch.object(self.agent, '_is_workflow_running', return_value=True):
            result = self.agent.execute_workflow(self.test_workflow["workflow_id"])
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["error"], "Workflow already running")
            mock_log_event.assert_called_with(
                "WORKFLOW_EXECUTION_REJECTED",
                self.agent.agent_id,
                {"workflow_id": self.test_workflow["workflow_id"], "reason": "Already running"}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_concurrent_workflow_execution"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_timeout(self, mock_log_event):
        """Test workflow execution timeout handling."""
        self.agent.create_workflow(self.test_workflow)
        with patch.object(self.agent, '_execute_step', side_effect=TimeoutError("Step timeout")):
            result = self.agent.execute_workflow(self.test_workflow["workflow_id"])
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["error"], "Workflow execution timeout")
            mock_log_event.assert_called_with(
                "WORKFLOW_EXECUTION_TIMEOUT",
                self.agent.agent_id,
                {"workflow_id": self.test_workflow["workflow_id"]}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_timeout"})

    @patch('agents.workflow_agent.log_event')
    def test_create_workflow_invalid_definition(self, mock_log_event):
        """Test workflow creation with invalid definition."""
        invalid_workflow = {"name": "Invalid"}  # Missing required fields
        result = self.agent.create_workflow(invalid_workflow)
        self.assertFalse(result)
        mock_log_event.assert_called_with(
            "WORKFLOW_CREATION_FAILED",
            self.agent.agent_id,
            {"error": "Invalid workflow definition"}
        )

    @patch('agents.workflow_agent.log_event')
    def test_execute_workflow_success(self, mock_log_event):
        """Test successful workflow execution."""
        # Setup: Create a workflow first
        self.agent.create_workflow(self.test_workflow)
        
        result = self.agent.execute_workflow("test_workflow_id")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "completed")
        mock_log_event.assert_called_with(
            "WORKFLOW_COMPLETED",
            self.agent.agent_id,
            {"workflow_id": "test_workflow_id"}
        )

    @patch('agents.workflow_agent.log_event')
    def test_execute_workflow_not_found(self, mock_log_event):
        """Test executing non-existent workflow."""
        result = self.agent.execute_workflow("nonexistent_id")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Workflow not found")
        mock_log_event.assert_called_with(
            "WORKFLOW_EXECUTION_FAILED",
            self.agent.agent_id,
            {"workflow_id": "nonexistent_id", "error": "Workflow not found"}
        )

    @patch('agents.workflow_agent.log_event')
    def test_list_workflows_empty(self, mock_log_event):
        """Test listing workflows when none exist."""
        workflows = self.agent.list_workflows()
        self.assertIsInstance(workflows, list)
        self.assertEqual(len(workflows), 0)
        mock_log_event.assert_called_with(
            "WORKFLOWS_LISTED",
            self.agent.agent_id,
            {"count": 0}
        )

    @patch('agents.workflow_agent.log_event')
    def test_list_workflows_with_items(self, mock_log_event):
        """Test listing workflows with existing items."""
        # Setup: Create a workflow first
        self.agent.create_workflow(self.test_workflow)
        
        workflows = self.agent.list_workflows()
        self.assertIsInstance(workflows, list)
        self.assertEqual(len(workflows), 1)
        self.assertEqual(workflows[0]["workflow_id"], "test_workflow_id")
        mock_log_event.assert_called_with(
            "WORKFLOWS_LISTED",
            self.agent.agent_id,
            {"count": 1}
        )

    @patch('agents.workflow_agent.log_event')
    def test_delete_workflow_success(self, mock_log_event):
        """Test successful workflow deletion."""
        # Setup: Create a workflow first
        self.agent.create_workflow(self.test_workflow)
        
        result = self.agent.delete_workflow("test_workflow_id")
        self.assertTrue(result)
        mock_log_event.assert_called_with(
            "WORKFLOW_DELETED",
            self.agent.agent_id,
            {"workflow_id": "test_workflow_id"}
        )

    @patch('agents.workflow_agent.log_event')
    def test_delete_workflow_not_found(self, mock_log_event):
        """Test deleting non-existent workflow."""
        result = self.agent.delete_workflow("nonexistent_id")
        self.assertFalse(result)
        mock_log_event.assert_called_with(
            "WORKFLOW_DELETION_FAILED",
            self.agent.agent_id,
            {"workflow_id": "nonexistent_id", "error": "Workflow not found"}
        )

    def test_workflow_persistence(self):
        """Test that workflows persist between operations."""
        # Create workflow
        self.agent.create_workflow(self.test_workflow)
        
        # Verify it exists
        workflows = self.agent.list_workflows()
        self.assertEqual(len(workflows), 1)
        
        # Delete it
        self.agent.delete_workflow("test_workflow_id")
        
        # Verify it's gone
        workflows = self.agent.list_workflows()
        self.assertEqual(len(workflows), 0)

    @patch('agents.workflow_agent.log_event')
    def test_workflow_step_retry_mechanism(self, mock_log_event):
        """Test workflow step retry mechanism for transient failures."""
        retry_workflow = {
            "workflow_id": "retry_test",
            "name": "Retry Test Workflow",
            "steps": [
                {
                    "step_id": "retry_step",
                    "name": "Retry Step",
                    "action": "flaky_action",
                    "params": {"max_retries": 3},
                    "retry_policy": {"max_attempts": 3, "delay_seconds": 1}
                }
            ]
        }
        
        self.agent.create_workflow(retry_workflow)
        
        # Mock the step execution to fail twice then succeed
        fail_count = [0]
        def mock_execute(*args, **kwargs):
            fail_count[0] += 1
            if fail_count[0] <= 2:
                raise Exception("Transient error")
            return {"status": "success"}
            
        with patch.object(self.agent, '_execute_step', side_effect=mock_execute):
            result = self.agent.execute_workflow("retry_test")
            self.assertEqual(result["status"], "completed")
            mock_log_event.assert_any_call(
                "WORKFLOW_STEP_RETRY",
                self.agent.agent_id,
                {"workflow_id": "retry_test", "step_id": "retry_step", "attempt": 2}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_step_retry_mechanism"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_conditional_execution(self, mock_log_event):
        """Test workflow conditional step execution based on previous step results."""
        conditional_workflow = {
            "workflow_id": "conditional_test",
            "name": "Conditional Workflow",
            "steps": [
                {
                    "step_id": "check_step",
                    "name": "Check Condition",
                    "action": "condition_check",
                    "params": {}
                },
                {
                    "step_id": "success_path",
                    "name": "Success Path",
                    "action": "success_action",
                    "condition": {"step_id": "check_step", "status": "success"}
                },
                {
                    "step_id": "failure_path",
                    "name": "Failure Path",
                    "action": "failure_action",
                    "condition": {"step_id": "check_step", "status": "error"}
                }
            ]
        }
        
        self.agent.create_workflow(conditional_workflow)
        
        with patch.object(self.agent, '_execute_step') as mock_execute:
            mock_execute.return_value = {"status": "success"}
            result = self.agent.execute_workflow("conditional_test")
            
            self.assertEqual(result["status"], "completed")
            self.assertEqual(mock_execute.call_count, 2)  # Only check_step and success_path should run
            mock_log_event.assert_any_call(
                "WORKFLOW_CONDITIONAL_EXECUTION",
                self.agent.agent_id,
                {"workflow_id": "conditional_test", "executed_step": "success_path"}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_conditional_execution"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_parallel_execution(self, mock_log_event):
        """Test parallel execution of workflow steps."""
        parallel_workflow = {
            "workflow_id": "parallel_test",
            "name": "Parallel Workflow",
            "steps": [
                {
                    "step_id": "parallel_1",
                    "name": "Parallel Step 1",
                    "action": "parallel_action",
                    "parallel": True
                },
                {
                    "step_id": "parallel_2",
                    "name": "Parallel Step 2",
                    "action": "parallel_action",
                    "parallel": True
                }
            ]
        }
        
        self.agent.create_workflow(parallel_workflow)
        
        with patch.object(self.agent, '_execute_step') as mock_execute:
            mock_execute.return_value = {"status": "success"}
            result = self.agent.execute_workflow("parallel_test")
            
            self.assertEqual(result["status"], "completed")
            mock_log_event.assert_any_call(
                "WORKFLOW_PARALLEL_EXECUTION",
                self.agent.agent_id,
                {"workflow_id": "parallel_test", "parallel_steps": 2}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_parallel_execution"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_resource_cleanup(self, mock_log_event):
        """Test proper resource cleanup after workflow execution."""
        cleanup_workflow = {
            "workflow_id": "cleanup_test",
            "name": "Cleanup Test Workflow",
            "steps": [
                {
                    "step_id": "resource_step",
                    "name": "Resource Step",
                    "action": "resource_action",
                    "cleanup_required": True
                }
            ]
        }
        
        self.agent.create_workflow(cleanup_workflow)
        
        with patch.object(self.agent, '_cleanup_resources') as mock_cleanup:
            result = self.agent.execute_workflow("cleanup_test")
            
            mock_cleanup.assert_called_once()
            mock_log_event.assert_any_call(
                "WORKFLOW_CLEANUP_COMPLETED",
                self.agent.agent_id,
                {"workflow_id": "cleanup_test"}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_resource_cleanup"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_version_compatibility(self, mock_log_event):
        """Test workflow version compatibility checks."""
        versioned_workflow = {
            "workflow_id": "version_test",
            "name": "Version Test Workflow",
            "version": "2.0",
            "min_agent_version": "1.5",
            "steps": [
                {
                    "step_id": "version_step",
                    "name": "Version Step",
                    "action": "version_action"
                }
            ]
        }
        
        # Test with compatible version
        with patch.object(self.agent, 'version', return_value="1.6"):
            result = self.agent.create_workflow(versioned_workflow)
            self.assertTrue(result)
            
        # Test with incompatible version
        with patch.object(self.agent, 'version', return_value="1.4"):
            result = self.agent.create_workflow(versioned_workflow)
            self.assertFalse(result)
            mock_log_event.assert_called_with(
                "WORKFLOW_VERSION_MISMATCH",
                self.agent.agent_id,
                {
                    "workflow_version": "2.0",
                    "min_agent_version": "1.5",
                    "current_agent_version": "1.4"
                }
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_version_compatibility"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_dynamic_step_generation(self, mock_log_event):
        """Test workflow steps that are dynamically generated based on previous step results."""
        dynamic_workflow = {
            "workflow_id": "dynamic_test",
            "name": "Dynamic Workflow",
            "steps": [
                {
                    "step_id": "generator_step",
                    "name": "Generate Steps",
                    "action": "step_generator",
                    "params": {"count": 3}
                }
            ],
            "dynamic": True
        }
        
        self.agent.create_workflow(dynamic_workflow)
        
        generated_steps = [
            {"step_id": f"dynamic_{i}", "action": "dynamic_action"}
            for i in range(3)
        ]
        
        with patch.object(self.agent, '_generate_dynamic_steps', return_value=generated_steps):
            result = self.agent.execute_workflow("dynamic_test")
            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(result["executed_steps"]), 4)  # generator + 3 dynamic
            mock_log_event.assert_any_call(
                "WORKFLOW_DYNAMIC_STEPS_GENERATED",
                self.agent.agent_id,
                {"workflow_id": "dynamic_test", "step_count": 3}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_dynamic_step_generation"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_rollback_mechanism(self, mock_log_event):
        """Test workflow rollback mechanism when steps fail."""
        rollback_workflow = {
            "workflow_id": "rollback_test",
            "name": "Rollback Workflow",
            "steps": [
                {
                    "step_id": "step1",
                    "name": "Step 1",
                    "action": "action1",
                    "rollback_action": "rollback1"
                },
                {
                    "step_id": "step2",
                    "name": "Step 2",
                    "action": "action2",
                    "rollback_action": "rollback2"
                }
            ]
        }
        
        self.agent.create_workflow(rollback_workflow)
        
        def mock_execute_step(step, *args):
            if step["step_id"] == "step2":
                raise Exception("Step 2 failed")
            return {"status": "success"}
            
        with patch.object(self.agent, '_execute_step', side_effect=mock_execute_step):
            with patch.object(self.agent, '_execute_rollback') as mock_rollback:
                result = self.agent.execute_workflow("rollback_test")
                self.assertEqual(result["status"], "error")
                mock_rollback.assert_called_once()
                mock_log_event.assert_any_call(
                    "WORKFLOW_ROLLBACK_INITIATED",
                    self.agent.agent_id,
                    {"workflow_id": "rollback_test", "failed_step": "step2"}
                )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_rollback_mechanism"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_state_persistence(self, mock_log_event):
        """Test workflow state persistence and recovery."""
        state_workflow = {
            "workflow_id": "state_test",
            "name": "State Workflow",
            "steps": [
                {
                    "step_id": "stateful_step",
                    "name": "Stateful Step",
                    "action": "state_action",
                    "persist_state": True
                }
            ]
        }
        
        self.agent.create_workflow(state_workflow)
        
        test_state = {"key": "value"}
        with patch('builtins.open', mock_open()) as mock_file:
            with patch.object(self.agent, '_load_workflow_state', return_value=test_state):
                result = self.agent.execute_workflow("state_test")
                self.assertEqual(result["status"], "completed")
                mock_log_event.assert_any_call(
                    "WORKFLOW_STATE_PERSISTED",
                    self.agent.agent_id,
                    {"workflow_id": "state_test", "state_size": len(str(test_state))}
                )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_state_persistence"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_metrics_collection(self, mock_log_event):
        """Test workflow execution metrics collection and reporting."""
        metrics_workflow = {
            "workflow_id": "metrics_test",
            "name": "Metrics Workflow",
            "steps": [
                {
                    "step_id": "measured_step",
                    "name": "Measured Step",
                    "action": "metric_action",
                    "collect_metrics": True
                }
            ]
        }
        
        self.agent.create_workflow(metrics_workflow)
        
        with patch.object(self.agent, '_collect_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "duration": 1.5,
                "memory_usage": 1024,
                "cpu_usage": 50
            }
            result = self.agent.execute_workflow("metrics_test")
            self.assertEqual(result["status"], "completed")
            self.assertIn("metrics", result)
            mock_log_event.assert_any_call(
                "WORKFLOW_METRICS_COLLECTED",
                self.agent.agent_id,
                {"workflow_id": "metrics_test", "metrics": mock_metrics.return_value}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_metrics_collection"})

    @patch('agents.workflow_agent.log_event')
    def test_workflow_dependency_resolution(self, mock_log_event):
        """Test workflow step dependency resolution and ordering."""
        dependency_workflow = {
            "workflow_id": "dependency_test",
            "name": "Dependency Workflow",
            "steps": [
                {
                    "step_id": "step_a",
                    "name": "Step A",
                    "action": "action_a"
                },
                {
                    "step_id": "step_b",
                    "name": "Step B",
                    "action": "action_b",
                    "depends_on": ["step_a"]
                },
                {
                    "step_id": "step_c",
                    "name": "Step C",
                    "action": "action_c",
                    "depends_on": ["step_b"]
                }
            ]
        }
        
        self.agent.create_workflow(dependency_workflow)
        
        execution_order = []
        def mock_execute_step(step, *args):
            execution_order.append(step["step_id"])
            return {"status": "success"}
            
        with patch.object(self.agent, '_execute_step', side_effect=mock_execute_step):
            result = self.agent.execute_workflow("dependency_test")
            self.assertEqual(result["status"], "completed")
            self.assertEqual(execution_order, ["step_a", "step_b", "step_c"])
            mock_log_event.assert_any_call(
                "WORKFLOW_DEPENDENCIES_RESOLVED",
                self.agent.agent_id,
                {"workflow_id": "dependency_test", "execution_order": execution_order}
            )
        log_event("TEST_PASSED", "TestWorkflowAgent", {"test": "test_workflow_dependency_resolution"})

if __name__ == "__main__":
    unittest.main() 