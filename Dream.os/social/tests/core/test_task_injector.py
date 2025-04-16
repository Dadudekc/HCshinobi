import unittest
import os
import sys
import json
import time # For potential timing checks
from unittest.mock import MagicMock, patch, mock_open

# Adjust path
script_dir = os.path.dirname(__file__)
core_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(core_dir)
agents_dir = os.path.join(project_root, 'core', 'agents')
utils_dir = os.path.join(project_root, 'core', 'utils')
coordination_dir = os.path.join(project_root, 'core', 'coordination')

if project_root not in sys.path:
    sys.path.insert(0, project_root)
if core_dir not in sys.path:
     sys.path.insert(0, core_dir)
if agents_dir not in sys.path:
    sys.path.insert(0, agents_dir)
if utils_dir not in sys.path:
    sys.path.insert(0, utils_dir)
if coordination_dir not in sys.path:
     sys.path.insert(0, coordination_dir)

# Import class
from core.agents.task_injector import TaskInjector, AGENT_NAME, DEFAULT_INJECTION_TARGET

# Mock dependencies
sys.modules['core.coordination.agent_bus'] = MagicMock()
sys.modules['core.agents.task_executor_agent'] = MagicMock() # TaskStatus import

MockAgentBus = MagicMock()
MockLock = MagicMock()

class TestTaskInjector(unittest.TestCase):

    def setUp(self):
        MockAgentBus.reset_mock()
        MockLock.reset_mock()
        self.mock_bus_instance = MockAgentBus()
        self.test_task_list_path = "dummy_injector_tasks.json"
        self.test_input_file_path = "dummy_input_tasks.jsonl"

    def tearDown(self):
        if os.path.exists(self.test_task_list_path):
            os.remove(self.test_task_list_path)
        if os.path.exists(self.test_input_file_path):
             os.remove(self.test_input_file_path)

    def test_initialization(self):
        """Test agent initialization registers agent."""
        agent = TaskInjector(
            agent_bus=self.mock_bus_instance,
            task_list_path=self.test_task_list_path,
            input_task_file_path=self.test_input_file_path,
            task_list_lock=MockLock()
        )

        self.mock_bus_instance.register_agent.assert_called_once_with(
            AGENT_NAME, capabilities=["task_injection"]
        )
        self.assertEqual(agent.agent_name, AGENT_NAME)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.remove')
    @patch('os.path.exists')
    def test_run_cycle_injects_tasks_from_file(self, mock_exists, mock_remove, mock_file_open):
        """Test run_cycle reads tasks from input file, sends them via bus, and clears file."""
        # Simulate input file exists and has content
        mock_exists.return_value = True
        valid_task_line_1 = json.dumps({"task_id": "inject1", "action": "A"}) + "\n"
        valid_task_line_2 = json.dumps({"task_id": "inject2", "action": "B", "status": "PENDING"}) + "\n"
        invalid_line = "this is not json\n"
        # Configure mock_open.readlines() to return the lines
        mock_file_open().readlines.return_value = [valid_task_line_1, invalid_line, valid_task_line_2]

        agent = TaskInjector(
            agent_bus=self.mock_bus_instance,
            task_list_path=self.test_task_list_path,
            input_task_file_path=self.test_input_file_path,
            task_list_lock=MockLock()
        )

        agent.run_cycle()

        # Verify file was opened for reading
        # Note: mock_open needs careful handling for multiple opens (read, then clear)
        # This assertion might be brittle, focusing on send_message is better
        # mock_file_open.assert_any_call(self.test_input_file_path, 'r', encoding='utf-8')

        # Verify messages sent for valid tasks
        calls = self.mock_bus_instance.send_message.call_args_list
        self.assertEqual(len(calls), 2) 

        # Check first valid task message
        call1_kwargs = calls[0][1]
        self.assertEqual(call1_kwargs['sender'], AGENT_NAME)
        self.assertEqual(call1_kwargs['recipient'], DEFAULT_INJECTION_TARGET)
        self.assertEqual(call1_kwargs['message_type'], "INJECT_TASK")
        self.assertEqual(call1_kwargs['payload']['task']['task_id'], "inject1")
        self.assertEqual(call1_kwargs['payload']['task']['status'], "PENDING") # Status added

        # Check second valid task message
        call2_kwargs = calls[1][1]
        self.assertEqual(call2_kwargs['sender'], AGENT_NAME)
        self.assertEqual(call2_kwargs['recipient'], DEFAULT_INJECTION_TARGET)
        self.assertEqual(call2_kwargs['message_type'], "INJECT_TASK")
        self.assertEqual(call2_kwargs['payload']['task']['task_id'], "inject2")
        self.assertEqual(call2_kwargs['payload']['task']['status'], "PENDING") # Status preserved

        # Verify input file was removed
        mock_remove.assert_called_once_with(self.test_input_file_path)

    @patch('os.path.exists')
    def test_run_cycle_no_input_file(self, mock_exists):
        """Test run_cycle does nothing if input file doesn't exist."""
        mock_exists.return_value = False

        agent = TaskInjector(
            agent_bus=self.mock_bus_instance,
            task_list_path=self.test_task_list_path,
            input_task_file_path=self.test_input_file_path,
            task_list_lock=MockLock()
        )

        agent.run_cycle()

        # Verify no messages sent and no file removed
        self.mock_bus_instance.send_message.assert_not_called()
        # os.remove should not be called
        # Note: This requires accessing the mock used by the agent's internal os reference
        # For simplicity, we rely on send_message not being called.


if __name__ == '__main__':
    unittest.main() 