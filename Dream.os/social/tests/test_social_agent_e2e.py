from unittest.mock import patch
import unittest

class TestSocialAgentE2E(unittest.TestCase):

    def setUp(self):
        self.responses = []
        self.mock_strategy_instance = patch('social_agent.strategy.Strategy').start()
        self.mock_log_event = patch('social_agent.logger.Logger').start()
        self.agent = SocialAgent(responses=self.responses, strategy_instance=self.mock_strategy_instance, logger=self.mock_log_event)
        self.message_queue = []

    def tearDown(self):
        patch.stopall()

    def test_cycle_post_success(self):
        """Test a cycle where a post command succeeds within the strategy."""
        # Simulate strategy post succeeding
        self.mock_strategy_instance.post.return_value = True
        self.mock_strategy_instance.post.side_effect = None # Clear any previous side effect

        # Add only a post message to the queue
        post_message = {"message_id": "e2e-post-success-01", "command": "post", "platform": "twitter", "details": {"text": "This post will succeed"}}
        self.message_queue = [post_message]

        # Simulate one loop iteration check & processing
        messages = self.agent.mailbox_handler.check_for_messages()
        self.assertEqual(len(messages), 1)
        for msg in messages:
            self.agent.process_incoming_message(msg) 
            
        # Assertions
        self.mock_strategy_instance.post.assert_called_once_with(text="This post will succeed", image_path=None, use_governance_context=False)
        self.assertEqual(len(self.responses), 1)
        response = self.responses[0]
        self.assertEqual(response['response_to'], "e2e-post-success-01")
        self.assertEqual(response['payload']['status'], "completed")
        # Check that the agent logged the PLATFORM_POST event with success=True
        self.mock_log_event.assert_any_call(
            "PLATFORM_POST", 
            self.agent.agent_id, 
            unittest.mock.ANY # Check details dict contains success: True
        )
        # Find the specific call and check the details
        found_log = False
        for call_args, _ in self.mock_log_event.call_args_list:
            if call_args[0] == "PLATFORM_POST":
                 self.assertTrue(call_args[2].get("success"))
                 found_log = True
                 break
        self.assertTrue(found_log, "PLATFORM_POST event with success=True was not logged.")

    @patch('time.sleep', return_value=None) # Prevent actual sleeping
    def test_cycle_post_error(self, mock_sleep):
        """Test a cycle where a post command fails within the strategy."""
        # Simulate strategy post failing
        self.mock_strategy_instance.post.return_value = False
        self.mock_strategy_instance.post.side_effect = None # Clear any previous side effect

        # Add only a post message to the queue
        post_message = {"message_id": "e2e-post-fail-01", "command": "post", "platform": "twitter", "details": {"text": "This post will fail"}}
        self.message_queue = [post_message]

        # Simulate one loop iteration check & processing
        messages = self.agent.mailbox_handler.check_for_messages()
        self.assertEqual(len(messages), 1)
        for msg in messages:
            self.agent.process_incoming_message(msg) 
            
        # Assertions
        self.mock_strategy_instance.post.assert_called_once_with(text="This post will fail", image_path=None, use_governance_context=False)
        self.assertEqual(len(self.responses), 1)
        response = self.responses[0]
        self.assertEqual(response['response_to'], "e2e-post-fail-01")
        self.assertEqual(response['payload']['status'], "failed") # Expecting failed status
        # Check that the agent logged the PLATFORM_POST event with success=False
        self.mock_log_event.assert_any_call(
            "PLATFORM_POST", 
            self.agent.agent_id, 
            unittest.mock.ANY # Check details dict contains success: False
        )
        # Find the specific call and check the details
        found_log = False
        for call_args, _ in self.mock_log_event.call_args_list:
            if call_args[0] == "PLATFORM_POST":
                 self.assertFalse(call_args[2].get("success"))
                 found_log = True
                 break
        self.assertTrue(found_log, "PLATFORM_POST event with success=False was not logged.")

    @patch('time.sleep', return_value=None) # Prevent actual sleeping
    def test_cycle_unknown_command(self, mock_sleep):
        """Test a cycle where an unknown command is received."""
        # Add an unknown command message
        unknown_message = {"message_id": "e2e-unknown-01", "command": "make_coffee", "platform": "kitchen"}
        self.message_queue = [unknown_message]

        # Simulate one loop iteration check & processing
        messages = self.agent.mailbox_handler.check_for_messages()
        self.assertEqual(len(messages), 1)
        for msg in messages:
            self.agent.process_incoming_message(msg) 
            
        # Assertions
        # No strategy methods should be called
        self.mock_strategy_instance.login.assert_not_called()
        self.mock_strategy_instance.post.assert_not_called()
        # Check that an error response was sent
        self.assertEqual(len(self.responses), 1)
        response = self.responses[0]
        self.assertEqual(response['response_to'], "e2e-unknown-01")
        self.assertEqual(response['payload']['status'], "error")
        self.assertIn("Unknown command: make_coffee", response['payload']['error_details'])
        # Check that a warning was logged
        self.mock_log_event.assert_any_call("AGENT_WARNING", self.agent.agent_id, unittest.mock.ANY)

if __name__ == '__main__':
    unittest.main() 