import unittest
import os
import json
import sys
from unittest.mock import MagicMock, patch, mock_open

# Adjust path to import agent code
# Assumes tests/core/ directory structure relative to project root
script_dir = os.path.dirname(__file__)
core_dir = os.path.dirname(script_dir) # core/
project_root = os.path.dirname(core_dir) # project root
agents_dir = os.path.join(project_root, 'core', 'agents')
utils_dir = os.path.join(project_root, 'core', 'utils')
coordination_dir = os.path.join(project_root, 'core', 'coordination')

# Add necessary directories to sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if core_dir not in sys.path:
     sys.path.insert(0, core_dir) # Needed for relative imports within core
if agents_dir not in sys.path:
    sys.path.insert(0, agents_dir)
if utils_dir not in sys.path:
    sys.path.insert(0, utils_dir)
if coordination_dir not in sys.path:
     sys.path.insert(0, coordination_dir)

# Import the class to test AFTER adjusting path
from core.agents.task_executor_agent import TaskExecutorAgent, TaskStatus, AGENT_NAME
# Mock dependencies that might be imported by the agent module
sys.modules['core.coordination.agent_bus'] = MagicMock()
sys.modules['core.utils.task_status_updater'] = MagicMock()

# Mock AgentBus and TaskStatusUpdater for testing
MockAgentBus = MagicMock()
MockTaskStatusUpdater = MagicMock()
MockLock = MagicMock()

class TestTaskExecutorAgent(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        # Reset mocks before each test
        MockAgentBus.reset_mock()
        MockTaskStatusUpdater.reset_mock()
        MockLock.reset_mock()

        # Mock the TaskStatusUpdater instance
        self.mock_updater_instance = MockTaskStatusUpdater()
        self.mock_updater_instance.lock = MockLock # Assign the mock lock to the updater instance

        # Mock AgentBus instance
        self.mock_bus_instance = MockAgentBus()

        self.test_task_list_path = "dummy_test_tasks.json"

    def tearDown(self):
        """Clean up after test methods."""
        if os.path.exists(self.test_task_list_path):
            os.remove(self.test_task_list_path)
        # Reset sys.modules mocks if they cause issues between tests
        # if 'core.coordination.agent_bus' in sys.modules:
        #     del sys.modules['core.coordination.agent_bus']
        # if 'core.utils.task_status_updater' in sys.modules:
        #     del sys.modules['core.utils.task_status_updater']


    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_initialization(self, mock_file_open, mock_exists):
        """Test agent initialization registers with the bus and handlers."""
        mock_exists.return_value = True # Simulate task file exists

        agent = TaskExecutorAgent(
            agent_bus=self.mock_bus_instance,
            task_status_updater=self.mock_updater_instance,
            task_list_path=self.test_task_list_path,
            task_list_lock=MockLock # Use the class mock here for simplicity
        )

        # Check registration calls
        self.mock_bus_instance.register_agent.assert_called_once_with(
            AGENT_NAME, capabilities=unittest.mock.ANY # Capabilities might change
        )
        # Check handler registration (adjust target/handler ref if needed)
        self.mock_bus_instance.register_handler.assert_called_once_with(
             AGENT_NAME, agent.handle_response
        )
        self.assertEqual(agent.agent_name, AGENT_NAME)
        self.assertEqual(agent.status_updater, self.mock_updater_instance)


    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_initialization_creates_task_file(self, mock_file_open, mock_exists):
        """Test agent initialization creates task file if it doesn't exist."""
        mock_exists.return_value = False # Simulate task file does NOT exist

        agent = TaskExecutorAgent(
            agent_bus=self.mock_bus_instance,
            task_status_updater=self.mock_updater_instance,
            task_list_path=self.test_task_list_path,
            task_list_lock=MockLock
        )

        # Check that open was called to write '[]'
        mock_file_open.assert_called_with(self.test_task_list_path, 'w')
        handle = mock_file_open()
        handle.write.assert_called_once_with('[]')

        # Check registration still happens
        self.mock_bus_instance.register_agent.assert_called_once()
        self.mock_bus_instance.register_handler.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    def test_load_tasks_valid(self, mock_file_open):
        """Test loading a valid task list."""
        valid_tasks = [{ "task_id": "t1", "status": "PENDING" }]
        mock_file_open.return_value.read.return_value = json.dumps(valid_tasks)

        agent = TaskExecutorAgent(
            agent_bus=self.mock_bus_instance,
            task_status_updater=self.mock_updater_instance,
            task_list_path=self.test_task_list_path,
            task_list_lock=MockLock
        )

        loaded_tasks = agent._load_tasks()

        self.assertEqual(loaded_tasks, valid_tasks)
        # Verify lock usage
        self.mock_updater_instance.lock.__enter__.assert_called_once()
        self.mock_updater_instance.lock.__exit__.assert_called_once()
        mock_file_open.assert_called_once_with(self.test_task_list_path, 'r', encoding='utf-8')

    @patch('builtins.open', new_callable=mock_open)
    def test_load_tasks_empty_list(self, mock_file_open):
        """Test loading an empty but valid task list."""
        mock_file_open.return_value.read.return_value = "[]"

        agent = TaskExecutorAgent(
            agent_bus=self.mock_bus_instance,
            task_status_updater=self.mock_updater_instance,
            task_list_path=self.test_task_list_path,
            task_list_lock=MockLock
        )

        loaded_tasks = agent._load_tasks()
        self.assertEqual(loaded_tasks, [])
        self.mock_updater_instance.lock.__enter__.assert_called_once()
        mock_file_open.assert_called_once_with(self.test_task_list_path, 'r', encoding='utf-8')

    @patch('builtins.open', new_callable=mock_open)
    def test_load_tasks_invalid_json(self, mock_file_open):
        """Test loading a file with invalid JSON content."""
        mock_file_open.return_value.read.return_value = "{\"invalid_json: "

        agent = TaskExecutorAgent(
            agent_bus=self.mock_bus_instance,
            task_status_updater=self.mock_updater_instance,
            task_list_path=self.test_task_list_path,
            task_list_lock=MockLock
        )

        loaded_tasks = agent._load_tasks()
        self.assertEqual(loaded_tasks, []) # Should return empty list on error
        self.mock_updater_instance.lock.__enter__.assert_called_once()

    @patch('builtins.open', new_callable=mock_open, side_effect=FileNotFoundError)
    def test_load_tasks_file_not_found(self, mock_file_open):
        """Test loading when the task file does not exist."""
        agent = TaskExecutorAgent(
            agent_bus=self.mock_bus_instance,
            task_status_updater=self.mock_updater_instance,
            task_list_path=self.test_task_list_path,
            task_list_lock=MockLock
        )

        loaded_tasks = agent._load_tasks()
        self.assertEqual(loaded_tasks, []) # Should return empty list on error
        self.mock_updater_instance.lock.__enter__.assert_called_once()
        # Verify the lock was attempted. open call assertion removed as side_effect prevents its full execution.

    def test_check_dependencies_no_deps(self):
        """Test checking dependencies when a task has none."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        task_no_deps = {"task_id": "t1", "status": TaskStatus.PENDING}
        all_tasks_map = {"t1": task_no_deps}
        self.assertTrue(agent._check_dependencies(task_no_deps, all_tasks_map))

    def test_check_dependencies_met(self):
        """Test checking dependencies when they are met."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        dep_task = {"task_id": "dep1", "status": TaskStatus.COMPLETED}
        task_with_deps = {"task_id": "t1", "status": TaskStatus.PENDING, "depends_on": ["dep1"]}
        all_tasks_map = {"t1": task_with_deps, "dep1": dep_task}
        self.assertTrue(agent._check_dependencies(task_with_deps, all_tasks_map))

    def test_check_dependencies_unmet_pending(self):
        """Test checking dependencies when a dependency is PENDING."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        dep_task = {"task_id": "dep1", "status": TaskStatus.PENDING}
        task_with_deps = {"task_id": "t1", "status": TaskStatus.PENDING, "depends_on": ["dep1"]}
        all_tasks_map = {"t1": task_with_deps, "dep1": dep_task}
        self.assertFalse(agent._check_dependencies(task_with_deps, all_tasks_map))

    def test_check_dependencies_unmet_failed(self):
        """Test checking dependencies when a dependency is FAILED."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        dep_task = {"task_id": "dep1", "status": TaskStatus.FAILED}
        task_with_deps = {"task_id": "t1", "status": TaskStatus.PENDING, "depends_on": ["dep1"]}
        all_tasks_map = {"t1": task_with_deps, "dep1": dep_task}
        self.assertFalse(agent._check_dependencies(task_with_deps, all_tasks_map))

    def test_check_dependencies_missing(self):
        """Test checking dependencies when a dependency task is missing from the map."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        task_with_deps = {"task_id": "t1", "status": TaskStatus.PENDING, "depends_on": ["dep_missing"]}
        all_tasks_map = {"t1": task_with_deps}
        # Should log a warning and return False
        with self.assertLogs(level='WARNING') as log:
            result = agent._check_dependencies(task_with_deps, all_tasks_map)
        self.assertFalse(result)
        self.assertIn("has unmet dependency: Task 'dep_missing' not found", log.output[0])

    # TODO: Add test for handle_response (success, failure, no task_id)
    def test_handle_response_success(self):
        """Test handling a successful task response."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        # Mock the message object directly instead of the module
        mock_message = MagicMock()
        mock_message.sender = "RespondingAgent"
        mock_message.status = "SUCCESS"
        mock_message.payload = {"result": "all done", "summary": "Task finished well."}
        mock_message.task_id = "task-abc"
        mock_message.id = "msg-1"

        agent.handle_response(mock_message)

        # Assert TaskStatusUpdater was called with normalized status and details
        self.mock_updater_instance.update_task_status.assert_called_once_with(
            task_id="task-abc",
            status=TaskStatus.COMPLETED, # Normalized from SUCCESS
            result_summary="Task finished well.", # Extracted from payload.summary
            error_details=None,
            originating_agent="RespondingAgent"
        )

    def test_handle_response_failure(self):
        """Test handling a failed task response."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        mock_message = MagicMock()
        mock_message.sender = "RespondingAgent"
        mock_message.status = "FAILED"
        mock_message.payload = {"error": "Something broke", "error_details": "Traceback..."}
        mock_message.task_id = "task-def"
        mock_message.id = "msg-2"

        agent.handle_response(mock_message)

        self.mock_updater_instance.update_task_status.assert_called_once_with(
            task_id="task-def",
            status=TaskStatus.FAILED, # Normalized from FAILED
            result_summary=None,
            error_details="Traceback...", # Extracted from payload.error_details
            originating_agent="RespondingAgent"
        )

    def test_handle_response_execution_error(self):
        """Test handling an execution error response."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        mock_message = MagicMock()
        mock_message.sender = "RespondingAgent"
        mock_message.status = "EXECUTION_ERROR"
        mock_message.payload = {"error": "Caught exception"}
        mock_message.task_id = "task-ghi"
        mock_message.id = "msg-3"

        agent.handle_response(mock_message)

        self.mock_updater_instance.update_task_status.assert_called_once_with(
            task_id="task-ghi",
            status=TaskStatus.ERROR, # Normalized from EXECUTION_ERROR
            result_summary=None,
            error_details="Caught exception", # Extracted from payload.error
            originating_agent="RespondingAgent"
        )

    def test_handle_response_no_task_id(self):
        """Test handling a response message missing the task_id."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        mock_message = MagicMock()
        mock_message.sender = "RespondingAgent"
        mock_message.status = "SUCCESS"
        mock_message.payload = {"result": "done"}
        # Missing task_id attribute or set to None
        mock_message.task_id = None 
        mock_message.id = "msg-4"

        with self.assertLogs(level='WARNING') as log:
            agent.handle_response(mock_message)

        # Assert TaskStatusUpdater was NOT called
        self.mock_updater_instance.update_task_status.assert_not_called()
        # Assert warning was logged
        self.assertIn("without a task_id", log.output[0])

    def test_handle_response_unhandled_status(self):
        """Test handling a response message with a status that doesn't map to COMPLETE/FAILED/ERROR."""
        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)
        mock_message = MagicMock()
        mock_message.sender = "RespondingAgent"
        mock_message.status = "IN_PROGRESS" # Status not handled for final update
        mock_message.payload = {"update": "still working"}
        mock_message.task_id = "task-jkl"
        mock_message.id = "msg-5"

        with self.assertLogs(level='WARNING') as log:
            agent.handle_response(mock_message)

        # Assert TaskStatusUpdater was NOT called
        self.mock_updater_instance.update_task_status.assert_not_called()
        # Assert warning was logged
        self.assertIn("with unhandled status 'IN_PROGRESS'", log.output[0])

    # TODO: Add test for run_cycle (dispatch pending, skip completed, skip unmet deps)
    @patch('core.agents.task_executor_agent.TaskExecutorAgent._load_tasks')
    @patch('core.agents.task_executor_agent.TaskExecutorAgent._check_dependencies')
    def test_run_cycle_dispatches_pending_task(self, mock_check_deps, mock_load_tasks):
        """Test run_cycle dispatches a PENDING task with met dependencies."""
        task1 = {"task_id": "t1", "status": TaskStatus.PENDING, "action": "ACTION_A", "priority": 1}
        mock_load_tasks.return_value = [task1]
        mock_check_deps.return_value = True # Assume dependencies are met
        self.mock_updater_instance.update_task_status.return_value = True # Assume status update succeeds
        self.mock_bus_instance.send_message.return_value = "msg-id-1" # Assume send succeeds

        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)

        agent.run_cycle()

        # Verify load and check_deps were called
        mock_load_tasks.assert_called_once()
        mock_check_deps.assert_called_once_with(task1, {task1['task_id']: task1})

        # Verify message sent
        self.mock_bus_instance.send_message.assert_called_once_with(
            sender=AGENT_NAME,
            recipient="CursorControlAgent", # Default based on current logic for unknown ACTION_A
            message_type="ACTION_A", # Uses action as type now
            payload={"action": "ACTION_A", "params": {}},
            task_id="t1"
        )

        # Verify status updated to DISPATCHED
        self.mock_updater_instance.update_task_status.assert_called_with(
            task_id="t1", status=TaskStatus.DISPATCHED
        )

    @patch('core.agents.task_executor_agent.TaskExecutorAgent._load_tasks')
    @patch('core.agents.task_executor_agent.TaskExecutorAgent._check_dependencies')
    def test_run_cycle_skips_completed_task(self, mock_check_deps, mock_load_tasks):
        """Test run_cycle skips tasks that are already COMPLETED."""
        task1 = {"task_id": "t1", "status": TaskStatus.COMPLETED, "action": "ACTION_A"}
        mock_load_tasks.return_value = [task1]

        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)

        agent.run_cycle()

        mock_load_tasks.assert_called_once()
        mock_check_deps.assert_not_called() # Shouldn't check deps for completed tasks
        self.mock_bus_instance.send_message.assert_not_called() # Shouldn't dispatch
        self.mock_updater_instance.update_task_status.assert_not_called() # Shouldn't update status

    @patch('core.agents.task_executor_agent.TaskExecutorAgent._load_tasks')
    @patch('core.agents.task_executor_agent.TaskExecutorAgent._check_dependencies')
    def test_run_cycle_skips_unmet_dependencies(self, mock_check_deps, mock_load_tasks):
        """Test run_cycle skips PENDING tasks with unmet dependencies."""
        task1 = {"task_id": "t1", "status": TaskStatus.PENDING, "action": "ACTION_A", "depends_on": ["t0"]}
        mock_load_tasks.return_value = [task1]
        mock_check_deps.return_value = False # Simulate unmet dependencies

        agent = TaskExecutorAgent(self.mock_bus_instance, self.mock_updater_instance, self.test_task_list_path, MockLock)

        agent.run_cycle()

        mock_load_tasks.assert_called_once()
        mock_check_deps.assert_called_once_with(task1, {task1['task_id']: task1})
        self.mock_bus_instance.send_message.assert_not_called() # Shouldn't dispatch
        # Status updater might be called for retry_count increment, but not for DISPATCHED/FAILED
        # Let's verify it wasn't called for DISPATCHED specifically
        calls = self.mock_updater_instance.update_task_status.call_args_list
        dispatched_call_found = any(call[1].get('status') == TaskStatus.DISPATCHED for call in calls)
        self.assertFalse(dispatched_call_found, "Task status should not be updated to DISPATCHED if dependencies are unmet.")


if __name__ == '__main__':
    unittest.main() 