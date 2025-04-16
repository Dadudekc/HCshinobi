import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import sys
import shutil
import tempfile
import time

# Add project root to sys.path to allow importing modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Module to test (from agents)
try:
    # Import the target module
    import agents.reflection_agent.reflection_agent as reflection_agent
    # Import dependency from core for mocking
    import core.governance_memory_engine as governance_memory_engine
    module_load_error = None
except ImportError as e:
    reflection_agent = None
    module_load_error = f"ImportError: {e}"
except SyntaxError as e:
    reflection_agent = None
    module_load_error = f"Syntax error in module: {e}"

# Sample Alert File Content (.md format)
SAMPLE_ALERT_MD = """# Test Alert
ALERT_ID: alert-test-reflect-001
AGENT_ID: executor-test
TASK_ID: task-test-abc
REASON: Halt due to unclear rule interpretation.
CONTEXT: Agent stopped at step 3.
RULE: GEN-001
"""

SAMPLE_ALERT_MD_NO_ID = """# Bad Alert
REASON: Missing ID.
"""

@unittest.skipIf(module_load_error, f"Skipping tests due to module load error: {module_load_error}")
class TestReflectionAgent(unittest.TestCase):

    def setUp(self):
        """Set up temporary runtime structure for AgentTest."""
        self.test_dir = tempfile.mkdtemp()
        self.agent_id = "AgentTest"
        # Use the target runtime structure
        self.runtime_dir = os.path.join(self.test_dir, "runtime") # Target runtime dir
        self.agent_base_path = os.path.join(self.runtime_dir, self.agent_id)
        self.inbox_dir = os.path.join(self.agent_base_path, "inbox")
        self.reflection_dir = os.path.join(self.agent_base_path, "reflection")
        self.reflection_log_file = os.path.join(self.reflection_dir, "reflection_log.md")

        # Create directories
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.reflection_dir, exist_ok=True)

        # Create mock alert file
        self.alert_file_path = os.path.join(self.inbox_dir, "alert1.md")
        with open(self.alert_file_path, 'w') as f: f.write(SAMPLE_ALERT_MD)

        # Mock sys.argv
        self.original_argv = sys.argv
        # Simulate running the script from its intended location
        sys.argv = [os.path.join("agents", "reflection_agent", "reflection_agent.py"), self.agent_id]

        # Override PROJECT_ROOT within the reflection_agent module for the test duration
        # This ensures it constructs runtime paths within our temp directory
        self.original_project_root = getattr(reflection_agent, 'PROJECT_ROOT', None)
        reflection_agent.PROJECT_ROOT = self.test_dir # Point its root to our temp dir

    def tearDown(self):
        """Clean up temporary directory and restore sys.argv and PROJECT_ROOT."""
        shutil.rmtree(self.test_dir)
        sys.argv = self.original_argv
        # Restore original project root if it was set
        if self.original_project_root is not None:
            reflection_agent.PROJECT_ROOT = self.original_project_root

    def test_parse_md_file(self):
        """Test parsing the key-value .md format."""
        parsed = reflection_agent.parse_md_file(self.alert_file_path)
        self.assertEqual(parsed.get("ALERT_ID"), "alert-test-reflect-001")
        self.assertEqual(parsed.get("AGENT_ID"), "executor-test")
        self.assertEqual(parsed.get("REASON"), "Halt due to unclear rule interpretation.")
        self.assertEqual(parsed.get("RULE"), "GEN-001")
        self.assertNotIn("# Test Alert", parsed) # Check comment ignored

    def test_decide_response_disagree_rule(self):
        """Test decision logic for unclear rule."""
        parsed_data = {"REASON": "Rule XYZ is ambiguous"}
        disposition, justification = reflection_agent.decide_response(parsed_data)
        self.assertEqual(disposition, "disagree_rule")

    def test_decide_response_disagree_monitor_halt(self):
        """Test decision logic for unexpected halt."""
        parsed_data = {"REASON": "Agent halted unexpectedly"}
        disposition, justification = reflection_agent.decide_response(parsed_data)
        self.assertEqual(disposition, "disagree_monitor")

    def test_decide_response_disagree_monitor_valid(self):
        """Test decision logic for seemingly valid halt."""
        parsed_data = {"REASON": "Expected behavior according to task spec"}
        disposition, justification = reflection_agent.decide_response(parsed_data)
        self.assertEqual(disposition, "disagree_monitor")

    def test_decide_response_agree(self):
        """Test default agree decision."""
        parsed_data = {"REASON": "Standard error occurred."}
        disposition, justification = reflection_agent.decide_response(parsed_data)
        self.assertEqual(disposition, "agree")

    @patch('core.governance_memory_engine.log_event') 
    def test_process_alert_file_success(self, mock_log_governance_event):
        """Test processing a valid alert file, checking logs and GME call."""
        reflection_agent.process_alert_file(self.alert_file_path, self.reflection_log_file, self.agent_id)

        # Check reflection log content
        self.assertTrue(os.path.exists(self.reflection_log_file))
        with open(self.reflection_log_file, 'r') as f:
            log_content = f.read()
        self.assertIn("**Alert ID:** alert-test-reflect-001", log_content)
        self.assertIn("**Disposition:** DISAGREE_RULE", log_content) # Based on reason
        self.assertIn("executor-test", log_content) # Original agent ID

        # Check that governance logger was called once
        mock_log_governance_event.assert_called_once()
        # Check arguments passed to governance logger
        call_args = mock_log_governance_event.call_args[0] # Get positional args
        call_kwargs = mock_log_governance_event.call_args[1] # Get keyword args
        # Combine positional into keyword based on function signature (event_type, agent_source, details)
        if len(call_args) > 0: call_kwargs['event_type'] = call_args[0]
        if len(call_args) > 1: call_kwargs['agent_source'] = call_args[1]
        if len(call_args) > 2: call_kwargs['details'] = call_args[2]

        self.assertEqual(call_kwargs.get('event_type'), "REFLECTION_LOGGED")
        self.assertEqual(call_kwargs.get('agent_source'), self.agent_id)
        details = call_kwargs.get('details', {})
        self.assertEqual(details.get("alert_id"), "alert-test-reflect-001")
        self.assertEqual(details.get("disposition"), "DISAGREE_RULE")

    @patch('core.governance_memory_engine.log_event')
    def test_process_alert_file_no_alert_id(self, mock_log_governance_event):
        """Test processing a file missing the ALERT_ID."""
        bad_alert_path = os.path.join(self.inbox_dir, "bad_alert.md")
        with open(bad_alert_path, 'w') as f:
            f.write(SAMPLE_ALERT_MD_NO_ID)

        reflection_agent.process_alert_file(bad_alert_path, self.reflection_log_file, self.agent_id)

        # Check reflection log WAS NOT written to
        self.assertFalse(os.path.exists(self.reflection_log_file), "Reflection log should not be created for bad alert.")
        # Check GME was NOT called
        mock_log_governance_event.assert_not_called()

    # Note: Testing the main loop directly is harder as it loops.
    # We could test it by mocking os.listdir and time.sleep, or by running
    # the main function in a separate thread and interrupting it.
    # For now, we focus on testing the core processing logic.

if __name__ == '__main__':
    if module_load_error:
        print(f"\nCannot run tests: Failed to import reflection_agent module or its dependencies.")
        print(f"Error: {module_load_error}")
    else:
        unittest.main() 