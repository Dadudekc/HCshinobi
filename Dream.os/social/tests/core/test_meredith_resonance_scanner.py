import unittest
import os
import sys
from unittest.mock import MagicMock, patch

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
from core.agents.meredith_resonance_scanner import MeredithResonanceScanner

# Mock dependencies
sys.modules['core.agent_bus'] = MagicMock() # Assuming agent uses this import path
sys.modules['core.coordination.agent_bus'] = MagicMock() # Also handle potential alt path

MockAgentBus = MagicMock()
MockMessage = MagicMock()

AGENT_NAME_TEST = "MeredithScanner_Test"

class TestMeredithResonanceScanner(unittest.TestCase):

    def setUp(self):
        MockAgentBus.reset_mock()
        MockMessage.reset_mock()
        self.mock_bus_instance = MockAgentBus()

    def test_initialization(self):
        """Test agent initialization registers agent and handler."""
        agent = MeredithResonanceScanner(
            agent_name=AGENT_NAME_TEST, 
            bus=self.mock_bus_instance, 
            config={}
        )

        self.assertEqual(agent.agent_name, AGENT_NAME_TEST)
        # Check registration call
        self.mock_bus_instance.register_agent.assert_called_once_with(
            AGENT_NAME_TEST, 
            ["social_media_scan", "sentiment_analysis", "meredith_topic"], # Expected capabilities
            agent.handle_message
        )
        # Check if specific handlers were registered (currently none are by default)
        self.mock_bus_instance.register_handler.assert_not_called()

    @patch('core.agents.meredith_resonance_scanner.MeredithResonanceScanner._perform_scan')
    def test_handle_message_request_scan(self, mock_perform_scan):
        """Test handle_message triggers _perform_scan for REQUEST_SCAN type."""
        agent = MeredithResonanceScanner(AGENT_NAME_TEST, self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "Dispatcher"
        mock_message.type = "REQUEST_SCAN"
        mock_message.payload = {"query": "Test Query"}
        mock_message.id = "scan-req-1"

        agent.handle_message(mock_message)

        # Verify _perform_scan was called with the payload
        mock_perform_scan.assert_called_once_with({"query": "Test Query"})

    @patch('core.agents.meredith_resonance_scanner.MeredithResonanceScanner._perform_scan')
    def test_handle_message_direct_message(self, mock_perform_scan):
        """Test handle_message logs direct messages but doesn't trigger scan."""
        agent = MeredithResonanceScanner(AGENT_NAME_TEST, self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "Admin"
        mock_message.recipient = AGENT_NAME_TEST # Direct message
        mock_message.type = "DIRECT_INFO"
        mock_message.payload = {"info": "System status ok"}
        mock_message.id = "direct-msg-1"

        # Use assertLogs to check logger output
        with self.assertLogs(level='INFO') as log:
            agent.handle_message(mock_message)
        
        # Verify scan was NOT called
        mock_perform_scan.assert_not_called()
        # Verify direct message was logged
        self.assertTrue(any("Received direct message" in msg for msg in log.output))

    @patch('core.agents.meredith_resonance_scanner.MeredithResonanceScanner._perform_scan')
    def test_handle_message_ignored_type(self, mock_perform_scan):
        """Test handle_message ignores irrelevant message types."""
        agent = MeredithResonanceScanner(AGENT_NAME_TEST, self.mock_bus_instance)
        mock_message = MagicMock()
        mock_message.sender = "SomeAgent"
        mock_message.recipient = "AnotherAgent"
        mock_message.type = "UNRELATED_EVENT"
        mock_message.payload = {}
        mock_message.id = "ignore-1"

        agent.handle_message(mock_message)

        # Verify scan was NOT called
        mock_perform_scan.assert_not_called()

    @patch('core.agents.meredith_resonance_scanner.time.time') # Mock time for predictable timestamp
    def test_perform_scan_sends_result(self, mock_time):
        """Test _perform_scan sends a SCAN_RESULT message via the bus."""
        mock_time.return_value = 1234567890.0
        agent = MeredithResonanceScanner(AGENT_NAME_TEST, self.mock_bus_instance)
        scan_params = {"query": "Test Query", "reply_to": "OriginalRequester"}

        agent._perform_scan(scan_params)

        # Verify send_message was called on the bus mock
        self.mock_bus_instance.send_message.assert_called_once()
        call_args = self.mock_bus_instance.send_message.call_args[1] # Get kwargs

        self.assertEqual(call_args['sender'], AGENT_NAME_TEST)
        self.assertEqual(call_args['recipient'], "OriginalRequester") # From reply_to param
        self.assertEqual(call_args['message_type'], "SCAN_RESULT")
        
        payload = call_args['payload']
        self.assertEqual(payload['status'], "scan_completed")
        self.assertEqual(payload['query'], "Test Query")
        self.assertIn('mention_count', payload)
        self.assertIn('resonance_score', payload)
        self.assertIn('sentiment', payload)
        self.assertIn('results', payload) # Check presence of simulated results
        self.assertEqual(payload['timestamp'], 1234567890.0)

    # TODO: Add tests for start/stop if background thread logic is enabled

if __name__ == '__main__':
    unittest.main() 