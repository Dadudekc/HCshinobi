import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from core.agents.agent_monitor_agent import AgentMonitorAgent

class TestAgentMonitorAgent(unittest.TestCase):
    def setUp(self):
        self.mock_bus_instance = MagicMock()
        self.test_log_file = "test_log_file.log"

    def test_log_event(self):
        agent = AgentMonitorAgent(agent_bus=self.mock_bus_instance, log_file_path=self.test_log_file)
        event_data = {"event": "test_event", "details": {"key": "value"}}
        agent._log_event(event_data)

        with open(self.test_log_file, "r") as f:
            logged_data = f.read()
            self.assertIn("test_event", logged_data)
            self.assertIn("key", logged_data)
            self.assertIn("value", logged_data)
            self.assertIn("log_timestamp", logged_data)

    @patch('core.agents.agent_monitor_agent.AgentMonitorAgent._log_event')
    def test_handle_event_message_task_completed(self, mock_log_event):
        """Test handle_event_message logs task_completed event."""
        agent = AgentMonitorAgent(agent_bus=self.mock_bus_instance, log_file_path=self.test_log_file)
        mock_message = MagicMock()
        mock_message.sender = "OtherAgent"
        mock_message.recipient = "TaskExecutorAgent" # Target for task status
        mock_message.type = "ACTION_RESPONSE"
        mock_message.status = "SUCCESS"
        mock_message.task_id = "task-comp-123"
        mock_message.id = "msg-c1"
        mock_message.payload = {"result": "ok"}
        mock_message.timestamp = datetime.now().isoformat()

        agent.handle_event_message(mock_message)

        mock_log_event.assert_called_once()
        logged_call_args = mock_log_event.call_args[0][0]
        self.assertEqual(logged_call_args['event'], "task_completed")
        self.assertEqual(logged_call_args['details']['task_id'], "task-comp-123")
        self.assertEqual(logged_call_args['details']['message_status'], "SUCCESS")

    @patch('core.agents.agent_monitor_agent.AgentMonitorAgent._log_event')
    def test_handle_event_message_task_failed(self, mock_log_event):
        """Test handle_event_message logs task_failed event."""
        agent = AgentMonitorAgent(agent_bus=self.mock_bus_instance, log_file_path=self.test_log_file)
        mock_message = MagicMock()
        mock_message.sender = "OtherAgent"
        mock_message.recipient = "TaskExecutorAgent"
        mock_message.type = "ACTION_RESPONSE"
        mock_message.status = "FAILED"
        mock_message.task_id = "task-fail-456"
        mock_message.id = "msg-f1"
        mock_message.payload = {"error": "bad thing"}
        mock_message.timestamp = datetime.now().isoformat()

        agent.handle_event_message(mock_message)

        mock_log_event.assert_called_once()
        logged_call_args = mock_log_event.call_args[0][0]
        self.assertEqual(logged_call_args['event'], "task_failed")
        self.assertEqual(logged_call_args['details']['task_id'], "task-fail-456")
        self.assertEqual(logged_call_args['details']['message_status'], "FAILED")

    @patch('core.agents.agent_monitor_agent.AgentMonitorAgent._log_event')
    def test_handle_event_message_generic_error(self, mock_log_event):
        """Test handle_event_message logs agent_error for ERROR type messages."""
        agent = AgentMonitorAgent(agent_bus=self.mock_bus_instance, log_file_path=self.test_log_file)
        mock_message = MagicMock()
        mock_message.sender = "SomeAgent"
        mock_message.recipient = "AnotherAgent"
        mock_message.type = "ERROR" # Explicit ERROR type
        mock_message.status = "ERROR_STATE"
        mock_message.task_id = None
        mock_message.id = "msg-e1"
        mock_message.payload = {"reason": "config missing"}
        mock_message.timestamp = datetime.now().isoformat()

        agent.handle_event_message(mock_message)

        mock_log_event.assert_called_once()
        logged_call_args = mock_log_event.call_args[0][0]
        self.assertEqual(logged_call_args['event'], "agent_error")
        self.assertEqual(logged_call_args['details']['sender'], "SomeAgent")
        self.assertEqual(logged_call_args['details']['message_type'], "ERROR")

    @patch('core.agents.agent_monitor_agent.AgentMonitorAgent._log_event')
    def test_handle_event_message_unknown(self, mock_log_event):
        """Test handle_event_message logs unknown_message_received for unhandled messages."""
        agent = AgentMonitorAgent(agent_bus=self.mock_bus_instance, log_file_path=self.test_log_file)
        mock_message = MagicMock()
        mock_message.sender = "WebApp"
        # Message is to TaskExecutorAgent, but status isn't SUCCESS/FAILED/ERROR
        mock_message.recipient = "TaskExecutorAgent" 
        mock_message.type = "QUERY"
        mock_message.status = "RECEIVED"
        mock_message.task_id = "task-unkn-789"
        mock_message.id = "msg-u1"
        mock_message.payload = {"data": "info"}
        mock_message.timestamp = datetime.now().isoformat()

        agent.handle_event_message(mock_message)

        mock_log_event.assert_called_once()
        logged_call_args = mock_log_event.call_args[0][0]
        self.assertEqual(logged_call_args['event'], "task_status_update") # Falls back to generic task update
        self.assertEqual(logged_call_args['details']['task_id'], "task-unkn-789")

    # TODO: Add test for thread safety of _log_event (might require more complex setup)

if __name__ == '__main__':
    unittest.main()