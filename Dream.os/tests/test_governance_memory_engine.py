import unittest
import os
import sys
import json
import tempfile
import shutil

# Add project root to sys.path to allow importing core modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Module to test (from core)
try:
    import core.governance_memory_engine as governance_memory_engine
    module_load_error = None
except ImportError as e:
    governance_memory_engine = None
    module_load_error = e

@unittest.skipIf(module_load_error, f"Skipping tests due to module load error: {module_load_error}")
class TestGovernanceMemoryEngine(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory and override the log file path for tests."""
        self.test_dir = tempfile.mkdtemp()
        self.test_log_file = os.path.join(self.test_dir, "test_governance_memory.jsonl")

        # Override the module's global log file path
        self.original_log_path = governance_memory_engine.GOVERNANCE_LOG_FILE
        governance_memory_engine.GOVERNANCE_LOG_FILE = self.test_log_file
        # Ensure the temporary directory exists for the test log file
        # The ensure_log_dir_exists function in the module should handle this,
        # but we create it here just in case for setup reliability.
        os.makedirs(os.path.dirname(self.test_log_file), exist_ok=True)
        print(f"NOTE: Redirected GME log path to: {self.test_log_file}")

    def tearDown(self):
        """Clean up the temporary directory and restore the original log path."""
        # Restore original log path
        governance_memory_engine.GOVERNANCE_LOG_FILE = self.original_log_path

        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)

    def test_log_single_event(self):
        """Test logging a single valid event."""
        event_type = "TEST_EVENT"
        agent_source = "TestAgent"
        details = {"key": "value", "number": 123}

        success = governance_memory_engine.log_event(event_type, agent_source, details)
        self.assertTrue(success, "log_event should return True on success.")

        # Verify the file was created and contains one line
        self.assertTrue(os.path.exists(self.test_log_file))
        with open(self.test_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1, "Log file should contain exactly one line.")

        # Verify the content of the logged event
        try:
            logged_data = json.loads(lines[0])
            self.assertIn("event_id", logged_data)
            self.assertTrue(logged_data["event_id"].startswith("event-"))
            self.assertIn("timestamp", logged_data)
            self.assertEqual(logged_data["event_type"], event_type)
            self.assertEqual(logged_data["agent_source"], agent_source)
            self.assertEqual(logged_data["details"], details)
        except json.JSONDecodeError:
            self.fail("Logged line is not valid JSON.")

    def test_log_multiple_events(self):
        """Test logging multiple events, ensuring they append correctly."""
        details1 = {"id": 1}
        details2 = {"id": 2, "status": "done"}

        governance_memory_engine.log_event("EVENT_A", "Agent1", details1)
        governance_memory_engine.log_event("EVENT_B", "Agent2", details2)

        self.assertTrue(os.path.exists(self.test_log_file))
        with open(self.test_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2, "Log file should contain two lines.")

        # Verify basic structure of both lines
        try:
            log1 = json.loads(lines[0])
            log2 = json.loads(lines[1])
            self.assertEqual(log1["event_type"], "EVENT_A")
            self.assertEqual(log1["details"], details1)
            self.assertEqual(log2["event_type"], "EVENT_B")
            self.assertEqual(log2["details"], details2)
            self.assertNotEqual(log1["event_id"], log2["event_id"])
        except (json.JSONDecodeError, IndexError, KeyError):
            self.fail("Logged lines are not valid JSON or missing expected keys.")

    def test_log_event_error_handling(self):
        """Test error handling (e.g., if the log file is not writable)."""
        # Make the file non-writable (difficult to do reliably cross-platform)
        # Instead, we can simulate an error by temporarily setting path to an invalid location
        invalid_path = os.path.join(self.test_dir, "non_existent_dir", "log.jsonl")
        governance_memory_engine.GOVERNANCE_LOG_FILE = invalid_path

        success = governance_memory_engine.log_event("FAIL_EVENT", "ErrorSource", {})
        self.assertFalse(success, "log_event should return False when writing fails.")

        # Restore the correct path for subsequent tests/teardown
        governance_memory_engine.GOVERNANCE_LOG_FILE = self.test_log_file

if __name__ == '__main__':
    if module_load_error:
        print(f"\nCannot run tests: Failed to import governance_memory_engine module from core.")
        print(f"Error: {module_load_error}")
    else:
        unittest.main() 