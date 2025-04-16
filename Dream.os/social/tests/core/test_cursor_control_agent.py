import unittest
import os
import sys
from unittest.mock import MagicMock, patch

# Adjust path to import agent code
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

# Import the class to test
from core.agents.cursor_control_agent import CursorControlAgent, AGENT_NAME

# Mock dependencies
sys.modules['core.coordination.agent_bus'] = MagicMock()
sys.modules['core.coordination.cursor_coordinator'] = MagicMock()

MockAgentBus = MagicMock()
MockCursorCoordinator = MagicMock()
MockMessage = MagicMock()

class TestCursorControlAgent(unittest.TestCase):

    def setUp(self):
        MockAgentBus.reset_mock()
        MockCursorCoordinator.reset_mock()
        MockMessage.reset_mock()
        self.mock_bus_instance = MockAgentBus()
        # Create a mock instance for the coordinator
        self.mock_coordinator_instance = MockCursorCoordinator()
        # Ensure target_instance_id is set, otherwise init might raise error
        self.mock_coordinator_instance.target_instance_id = "mock_instance_123"

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_initialization(self, mock_coordinator_class):
        """Test agent initialization registers agent and handlers."""
        # Make the class return our mock instance when called
        mock_coordinator_class.return_value = self.mock_coordinator_instance

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance, launch_new_instance=False)

        mock_coordinator_class.assert_called_once_with(launch_new_instance=False)
        self.mock_bus_instance.register_agent.assert_called_once_with(
            AGENT_NAME, capabilities=["cursor_control"]
        )
        # Check handler registrations
        expected_handlers = [(AGENT_NAME, agent.handle_message), ("CURSOR_COMMAND", agent.handle_message)]
        actual_calls = self.mock_bus_instance.register_handler.call_args_list
        self.assertEqual(len(actual_calls), len(expected_handlers))
        actual_handlers = sorted([(call[0][0], call[0][1]) for call in actual_calls])
        self.assertEqual(actual_handlers, sorted(expected_handlers))
        self.assertEqual(agent.coordinator, self.mock_coordinator_instance)

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_initialization_coordinator_fails(self, mock_coordinator_class):
        """Test agent initialization when CursorCoordinator fails."""
        # Simulate coordinator failing to find target instance
        mock_failing_coordinator = MagicMock()
        mock_failing_coordinator.target_instance_id = None # Simulate failure
        mock_coordinator_class.return_value = mock_failing_coordinator

        # Agent init should still proceed but coordinator will be None or unusable
        # (Actual behavior depends on agent's error handling - currently logs error)
        # We won't assert on coordinator == None as the error handling might change.
        # Just ensure it doesn't crash and doesn't register if coordinator fails severely (if designed that way)
        # Current design registers anyway, so we check that.
        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)

        # Assert registration still happened (based on current agent implementation)
        self.mock_bus_instance.register_agent.assert_called_once()
        self.assertEqual(len(self.mock_bus_instance.register_handler.call_args_list), 2)
        # Assert coordinator attribute might be set but is the failing mock
        self.assertEqual(agent.coordinator, mock_failing_coordinator)

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_get_editor_content_success(self, mock_coordinator_class):
        """Test handle_message for GET_EDITOR_CONTENT action (Success)."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        # Simulate coordinator returning content
        expected_content = "print('Hello')"
        self.mock_coordinator_instance.get_editor_content.return_value = expected_content

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)

        # Create mock message
        mock_message = MagicMock()
        mock_message.sender = "RequestingAgent"
        mock_message.payload = {"action": "GET_EDITOR_CONTENT", "params": {}}
        mock_message.id = "req-1"
        mock_message.task_id = "task-content"

        agent.handle_message(mock_message)

        # Verify coordinator method was called
        self.mock_coordinator_instance.get_editor_content.assert_called_once()
        # Verify response sent via bus
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1] # Get kwargs
        self.assertEqual(call_args['sender'], AGENT_NAME)
        self.assertEqual(call_args['recipient'], "RequestingAgent")
        self.assertEqual(call_args['message_type'], "GET_EDITOR_CONTENT_RESPONSE")
        self.assertEqual(call_args['status'], "SUCCESS")
        self.assertEqual(call_args['payload']['content'], expected_content)
        self.assertEqual(call_args['request_id'], "req-1")
        self.assertEqual(call_args['task_id'], "task-content")

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_get_editor_content_fail(self, mock_coordinator_class):
        """Test handle_message for GET_EDITOR_CONTENT action (Coordinator fails)."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        # Simulate coordinator failing to get content
        self.mock_coordinator_instance.get_editor_content.return_value = None

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)

        mock_message = MagicMock()
        mock_message.sender = "RequestingAgent"
        mock_message.payload = {"action": "GET_EDITOR_CONTENT", "params": {}}
        mock_message.id = "req-2"
        mock_message.task_id = "task-content-fail"

        agent.handle_message(mock_message)

        self.mock_coordinator_instance.get_editor_content.assert_called_once()
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "FAILED")
        self.assertIsNone(call_args['payload'].get('content'))

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_run_terminal_success(self, mock_coordinator_class):
        """Test handle_message for RUN_TERMINAL_COMMAND action (Success)."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        # Simulate coordinator successfully running command
        self.mock_coordinator_instance.run_terminal_command.return_value = True
        test_command = "echo test"

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        mock_message.payload = {"action": "RUN_TERMINAL_COMMAND", "params": {"command": test_command, "wait": False}}
        mock_message.id = "req-term-1"
        mock_message.task_id = "task-term-succ"

        agent.handle_message(mock_message)

        # Verify coordinator called with correct args
        self.mock_coordinator_instance.run_terminal_command.assert_called_once_with(test_command, wait=False)
        # Verify response sent via bus
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "SUCCESS")
        self.assertEqual(call_args['payload']['command_executed'], test_command)
        self.assertTrue(call_args['payload']['success'])
        self.assertEqual(call_args['request_id'], "req-term-1")

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_run_terminal_fail(self, mock_coordinator_class):
        """Test handle_message for RUN_TERMINAL_COMMAND action (Coordinator fails)."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        # Simulate coordinator failing to run command
        self.mock_coordinator_instance.run_terminal_command.return_value = False
        test_command = "bad_command"

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        mock_message.payload = {"action": "RUN_TERMINAL_COMMAND", "params": {"command": test_command}}
        mock_message.id = "req-term-2"
        mock_message.task_id = "task-term-fail"

        agent.handle_message(mock_message)

        self.mock_coordinator_instance.run_terminal_command.assert_called_once_with(test_command, wait=True) # Default wait
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "FAILED")
        self.assertFalse(call_args['payload']['success'])

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_run_terminal_missing_command(self, mock_coordinator_class):
        """Test handle_message for RUN_TERMINAL_COMMAND action with missing command param."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        # Missing 'command' in params
        mock_message.payload = {"action": "RUN_TERMINAL_COMMAND", "params": {}} 
        mock_message.id = "req-term-3"
        mock_message.task_id = "task-term-badreq"

        agent.handle_message(mock_message)

        # Coordinator should NOT be called
        self.mock_coordinator_instance.run_terminal_command.assert_not_called()
        # Verify BAD_REQUEST response sent via bus
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "BAD_REQUEST")
        self.assertIn("Missing 'command' parameter", call_args['payload']['error'])

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_get_terminal_output_success(self, mock_coordinator_class):
        """Test handle_message for GET_TERMINAL_OUTPUT action (Success)."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        expected_output = "line1\nline2"
        self.mock_coordinator_instance.get_terminal_output.return_value = expected_output

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        mock_message.payload = {"action": "GET_TERMINAL_OUTPUT", "params": {"max_lines": 100}}
        mock_message.id = "req-term-out-1"
        mock_message.task_id = "task-term-out-succ"

        agent.handle_message(mock_message)

        self.mock_coordinator_instance.get_terminal_output.assert_called_once_with(max_lines=100)
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "SUCCESS") # Assumes success even if output is None now
        self.assertEqual(call_args['payload']['output'], expected_output)

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_get_terminal_output_fail(self, mock_coordinator_class):
        """Test handle_message for GET_TERMINAL_OUTPUT action (Coordinator returns None)."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        self.mock_coordinator_instance.get_terminal_output.return_value = None # Simulate failure

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        mock_message.payload = {"action": "GET_TERMINAL_OUTPUT", "params": {}}
        mock_message.id = "req-term-out-2"
        mock_message.task_id = "task-term-out-fail"

        agent.handle_message(mock_message)

        self.mock_coordinator_instance.get_terminal_output.assert_called_once_with(max_lines=None)
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "FAILED") # Check added for None return
        self.assertIsNone(call_args['payload']['output'])
        self.assertIn("Failed to retrieve terminal output", call_args['payload']['error'])

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_open_file_success(self, mock_coordinator_class):
        """Test handle_message for OPEN_FILE action (Success)."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        self.mock_coordinator_instance.open_file_in_editor.return_value = True
        test_path = "/path/to/file.py"

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        mock_message.payload = {"action": "OPEN_FILE", "params": {"file_path": test_path}}
        mock_message.id = "req-open-1"
        mock_message.task_id = "task-open-succ"

        agent.handle_message(mock_message)

        self.mock_coordinator_instance.open_file_in_editor.assert_called_once_with(test_path)
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "SUCCESS")
        self.assertEqual(call_args['payload']['file_opened'], test_path)
        self.assertTrue(call_args['payload']['success'])

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_open_file_fail(self, mock_coordinator_class):
        """Test handle_message for OPEN_FILE action (Coordinator fails)."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        self.mock_coordinator_instance.open_file_in_editor.return_value = False
        test_path = "/path/to/other.py"

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        mock_message.payload = {"action": "OPEN_FILE", "params": {"file_path": test_path}}
        mock_message.id = "req-open-2"
        mock_message.task_id = "task-open-fail"

        agent.handle_message(mock_message)

        self.mock_coordinator_instance.open_file_in_editor.assert_called_once_with(test_path)
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "FAILED")
        self.assertFalse(call_args['payload']['success'])

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_open_file_missing_path(self, mock_coordinator_class):
        """Test handle_message for OPEN_FILE action with missing file_path param."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        mock_message.payload = {"action": "OPEN_FILE", "params": {}} # Missing path
        mock_message.id = "req-open-3"
        mock_message.task_id = "task-open-badreq"

        agent.handle_message(mock_message)

        self.mock_coordinator_instance.open_file_in_editor.assert_not_called()
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "BAD_REQUEST")
        self.assertIn("Missing 'file_path' parameter", call_args['payload']['error'])

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_unknown_action(self, mock_coordinator_class):
        """Test handle_message with an unknown action."""
        mock_coordinator_class.return_value = self.mock_coordinator_instance
        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "ExecutorAgent"
        mock_message.payload = {"action": "DO_MAGIC", "params": {}}
        mock_message.id = "req-unk-1"
        mock_message.task_id = "task-unknown"

        agent.handle_message(mock_message)

        # Assert no coordinator methods for specific actions were called
        self.mock_coordinator_instance.run_terminal_command.assert_not_called()
        self.mock_coordinator_instance.get_editor_content.assert_not_called()
        # Verify UNKNOWN_ACTION response sent
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['status'], "UNKNOWN_ACTION")
        self.assertIn("Unsupported action: DO_MAGIC", call_args['payload']['error'])

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_handle_message_no_coordinator(self, mock_coordinator_class):
        """Test handle_message behavior when coordinator failed to initialize."""
        # Simulate coordinator failure during init
        mock_failing_coordinator = MagicMock()
        mock_failing_coordinator.target_instance_id = None
        mock_coordinator_class.return_value = mock_failing_coordinator

        # Initialize agent (it should log error but store the failing coordinator)
        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        # Manually set coordinator to None *after* init for this test case,
        # as the agent's init currently proceeds even if coordinator fails.
        # A stricter init might set self.coordinator = None directly.
        agent.coordinator = None

        # Create a valid message
        mock_message = MagicMock()
        mock_message.sender = "RequestingAgent"
        mock_message.payload = {"action": "GET_EDITOR_CONTENT", "params": {}}
        mock_message.id = "req-no-coord"
        mock_message.task_id = "task-no-coord"

        # Handle the message
        agent.handle_message(mock_message)

        # Verify no coordinator methods were called
        self.mock_coordinator_instance.get_editor_content.assert_not_called()
        # Verify an ERROR response was sent back via the bus
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1]
        self.assertEqual(call_args['sender'], AGENT_NAME)
        self.assertEqual(call_args['recipient'], "RequestingAgent")
        self.assertEqual(call_args['message_type'], "ERROR")
        self.assertEqual(call_args['status'], "ERROR") # Agent sends status=ERROR too
        self.assertIn("Coordinator unavailable", call_args['payload']['error'])
        self.assertEqual(call_args['request_id'], "req-no-coord")

    # TODO: Test handle_message when coordinator is None
    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_shutdown_closes_launched_coordinator(self, mock_coordinator_class):
        """Test shutdown calls close_cursor if coordinator was launched."""
        # Simulate coordinator that *was* launched by the agent
        self.mock_coordinator_instance._was_launched = True
        mock_coordinator_class.return_value = self.mock_coordinator_instance

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance, launch_new_instance=True)
        agent.shutdown()

        # Verify close_cursor was called
        self.mock_coordinator_instance.close_cursor.assert_called_once_with(force=True)

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_shutdown_does_not_close_existing_coordinator(self, mock_coordinator_class):
        """Test shutdown does NOT call close_cursor if coordinator was not launched."""
        # Simulate coordinator that was *not* launched by the agent
        self.mock_coordinator_instance._was_launched = False
        mock_coordinator_class.return_value = self.mock_coordinator_instance

        agent = CursorControlAgent(agent_bus=self.mock_bus_instance, launch_new_instance=False)
        agent.shutdown()

        # Verify close_cursor was NOT called
        self.mock_coordinator_instance.close_cursor.assert_not_called()

    @patch('core.agents.cursor_control_agent.CursorCoordinator')
    def test_shutdown_handles_no_coordinator(self, mock_coordinator_class):
        """Test shutdown handles the case where coordinator is None."""
        # Simulate coordinator failing during init
        mock_failing_coordinator = MagicMock()
        mock_failing_coordinator.target_instance_id = None
        mock_coordinator_class.return_value = mock_failing_coordinator
        agent = CursorControlAgent(agent_bus=self.mock_bus_instance)
        agent.coordinator = None # Ensure coordinator is None for the test
        
        # Shutdown should execute without error
        try:
            agent.shutdown()
        except Exception as e:
            self.fail(f"agent.shutdown() raised exception unexpectedly: {e}")
        
        # Verify no attempt was made to close a non-existent coordinator
        self.mock_coordinator_instance.close_cursor.assert_not_called()

if __name__ == '__main__':
    unittest.main() 