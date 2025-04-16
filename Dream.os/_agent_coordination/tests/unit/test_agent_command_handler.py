import unittest
from unittest.mock import MagicMock, call
import logging

# Adjust the import path based on your project structure
# Assumes tests/ is at the same level as agents/
from agents.core.agent_command_handler import CommandHandler 

# Disable logging during tests unless specifically needed
logging.disable(logging.CRITICAL)

class TestAgentCommandHandlerTerminate(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.mock_filesystem = MagicMock()
        self.mock_memory = MagicMock()
        # Configure mock memory's get method to return None by default
        self.mock_memory.get.return_value = None 
        self.mock_logger = MagicMock()
        
        self.agent_id = "TestAgentTerminate"
        self.specialization = "testing"
        
        self.handler = CommandHandler(
            agent_id=self.agent_id,
            specialization=self.specialization,
            filesystem=self.mock_filesystem,
            memory=self.mock_memory,
            logger=self.mock_logger
        )

    def test_handle_terminate_sets_flag_and_reason(self):
        """Verify handle_terminate sets the correct flags in memory."""
        test_reason = "Test shutdown reason"
        params = {"reason": test_reason}
        
        # Call the handler via the main dispatcher
        result = self.handler.handle_command("terminate", params)

        # Check assertions
        self.assertEqual(result["status"], "success")
        self.mock_logger.warning.assert_called_once_with(
            f"Termination requested by command. Reason: {test_reason}. Delay: 0s"
        )
        # Check that memory.set was called correctly for both flags
        expected_calls = [
            call.set("terminate_signal", True),
            call.set("terminate_reason", test_reason)
        ]
        self.mock_memory.assert_has_calls(expected_calls, any_order=False)
        self.mock_logger.info.assert_any_call("Terminate signal set in memory.") # Check log message

    def test_handle_terminate_default_reason(self):
        """Verify handle_terminate uses a default reason if none provided."""
        params = {} # No reason provided
        default_reason = "No reason provided"
        
        self.handler.handle_command("terminate", params)

        self.mock_logger.warning.assert_called_once_with(
            f"Termination requested by command. Reason: {default_reason}. Delay: 0s"
        )
        expected_calls = [
            call.set("terminate_signal", True),
            call.set("terminate_reason", default_reason)
        ]
        self.mock_memory.assert_has_calls(expected_calls, any_order=False)

    def test_handle_terminate_handles_delay_param(self):
        """Verify handle_terminate logs the delay parameter (even if not implemented)."""
        test_reason = "Delayed shutdown"
        test_delay = 30
        params = {"reason": test_reason, "delay_seconds": test_delay}
        
        self.handler.handle_command("terminate", params)

        self.mock_logger.warning.assert_called_once_with(
            f"Termination requested by command. Reason: {test_reason}. Delay: {test_delay}s"
        )
        # Ensure flags are still set correctly
        expected_calls = [
            call.set("terminate_signal", True),
            call.set("terminate_reason", test_reason)
        ]
        self.mock_memory.assert_has_calls(expected_calls, any_order=False)

if __name__ == '__main__':
    unittest.main() 