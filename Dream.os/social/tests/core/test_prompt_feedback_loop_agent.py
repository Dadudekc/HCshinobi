import unittest
from unittest.mock import patch, Mock, mock_open, call
from core.agents.prompt_feedback_loop_agent import PromptFeedbackLoopAgent
from core.utils.lock import MockLock
import sys

class TestPromptFeedbackLoopAgent(unittest.TestCase):
    def setUp(self):
        self.mock_bus_instance = Mock()
        self.test_task_list_path = "test_task_list.json"

    def test_mark_repair_triggered_success(self):
        """Test marking a task as having triggered repair."""
        agent = PromptFeedbackLoopAgent(self.mock_bus_instance, self.test_task_list_path, MockLock())
        tasks = [
            {"task_id": "t1", "status": "FAILED"},
            {"task_id": "t2", "status": "FAILED", "repair_attempts": 1}
        ]
        target_task_id = "t1"

        # Mock datetime to control timestamp
        with patch('core.agents.prompt_feedback_loop_agent.datetime') as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = "mock_iso_timestamp"
            
            found = agent._mark_repair_triggered(tasks, target_task_id)

            self.assertTrue(found)
            # Find the updated task
            updated_task = next((t for t in tasks if t["task_id"] == target_task_id), None)
            self.assertIsNotNone(updated_task)
            self.assertEqual(updated_task.get("repair_attempts"), 1)
            self.assertEqual(updated_task.get("last_updated"), "mock_iso_timestamp")

    def test_mark_repair_triggered_increment(self):
        """Test incrementing the repair attempts count."""
        agent = PromptFeedbackLoopAgent(self.mock_bus_instance, self.test_task_list_path, MockLock())
        tasks = [
            {"task_id": "t1", "status": "FAILED"},
            {"task_id": "t2", "status": "FAILED", "repair_attempts": 1}
        ]
        target_task_id = "t2"

        with patch('core.agents.prompt_feedback_loop_agent.datetime') as mock_dt:
            mock_dt.now.return_value.isoformat.return_value = "mock_iso_timestamp_2"
            
            found = agent._mark_repair_triggered(tasks, target_task_id)

            self.assertTrue(found)
            updated_task = next((t for t in tasks if t["task_id"] == target_task_id), None)
            self.assertIsNotNone(updated_task)
            self.assertEqual(updated_task.get("repair_attempts"), 2)
            self.assertEqual(updated_task.get("last_updated"), "mock_iso_timestamp_2")

    def test_mark_repair_triggered_not_found(self):
        """Test behavior when the target task ID is not found."""
        agent = PromptFeedbackLoopAgent(self.mock_bus_instance, self.test_task_list_path, MockLock())
        tasks = [{"task_id": "t1", "status": "FAILED"}]
        target_task_id = "t_not_found"
        
        found = agent._mark_repair_triggered(tasks, target_task_id)
        self.assertFalse(found)
        # Ensure original list is unchanged
        self.assertEqual(tasks[0].get("repair_attempts"), None)

    # TODO: Test _load_tasks / _save_tasks (if not refactored)
    @patch('core.agents.prompt_feedback_loop_agent.uuid')
    def test_create_diagnostic_task_run_terminal(self, mock_uuid):
        """Test creating a diagnostic task for a failed RUN_TERMINAL_COMMAND."""
        mock_uuid.uuid4.return_value.hex = "uuid123"
        agent = PromptFeedbackLoopAgent(self.mock_bus_instance, self.test_task_list_path, MockLock())
        failed_task = {
            "task_id": "orig_term_1",
            "action": "RUN_TERMINAL_COMMAND",
            "params": {"command": "python build.py"},
            "status": "FAILED",
            "last_response": {"error": "Build failed"}
        }

        diag_task = agent._create_diagnostic_task(failed_task)

        self.assertEqual(diag_task["status"], TaskStatus.PENDING)
        self.assertTrue(diag_task["task_id"].startswith("repair_orig_term_1_"))
        self.assertEqual(diag_task["task_type"], "diagnose_RUN_TERMINAL_COMMAND_failure")
        self.assertEqual(diag_task["action"], "RUN_TERMINAL_COMMAND")
        self.assertEqual(diag_task["depends_on"], ["orig_term_1"])
        self.assertEqual(diag_task["priority"], 1)
        self.assertEqual(diag_task["target_agent"], "CursorControlAgent")
        # Check params
        params = diag_task["params"]
        self.assertEqual(params["related_task_id"], "orig_term_1")
        self.assertIn("Build failed", params["failure_reason"])
        self.assertIn("pwd", params["command"])
        self.assertIn("ls -alh", params["command"])
        self.assertIn("check recent logs", params["command"]) # Specific to build/py command

    @patch('core.agents.prompt_feedback_loop_agent.uuid')
    def test_create_diagnostic_task_open_file(self, mock_uuid):
        """Test creating a diagnostic task for a failed OPEN_FILE."""
        mock_uuid.uuid4.return_value.hex = "uuid456"
        agent = PromptFeedbackLoopAgent(self.mock_bus_instance, self.test_task_list_path, MockLock())
        failed_task = {
            "task_id": "orig_open_1",
            "action": "OPEN_FILE",
            "params": {"file_path": "/data/important.txt"},
            "status": "FAILED",
            "last_response": {"error": "Permission denied"}
        }

        diag_task = agent._create_diagnostic_task(failed_task)

        self.assertEqual(diag_task["task_type"], "diagnose_OPEN_FILE_failure")
        self.assertEqual(diag_task["action"], "RUN_TERMINAL_COMMAND")
        # Check params
        params = diag_task["params"]
        self.assertIn("Checking file status for: /data/important.txt", params["command"])
        self.assertIn("ls -ld \"/data/important.txt\"", params["command"]) # Check specific command

    @patch('core.agents.prompt_feedback_loop_agent.uuid')
    def test_create_diagnostic_task_cursor_action(self, mock_uuid):
        """Test creating a diagnostic task for a failed cursor-specific action."""
        mock_uuid.uuid4.return_value.hex = "uuid789"
        agent = PromptFeedbackLoopAgent(self.mock_bus_instance, self.test_task_list_path, MockLock())
        failed_task = {
            "task_id": "orig_cursor_1",
            "action": "GET_EDITOR_CONTENT",
            "params": {},
            "status": "ERROR",
            "last_response": {"error": "No response from editor"}
        }

        diag_task = agent._create_diagnostic_task(failed_task)

        self.assertEqual(diag_task["task_type"], "diagnose_GET_EDITOR_CONTENT_failure")
        self.assertEqual(diag_task["action"], "RUN_TERMINAL_COMMAND")
        # Check params
        params = diag_task["params"]
        self.assertIn("Checking Cursor process status", params["command"])
        # Check for platform-specific process check (will depend on test environment)
        if sys.platform == "win32":
             self.assertIn("tasklist | findstr Cursor", params["command"])
        else:
             self.assertIn("ps aux | grep -i [C]ursor", params["command"])

    @patch('core.agents.prompt_feedback_loop_agent.uuid')
    def test_create_diagnostic_task_unknown_action(self, mock_uuid):
        """Test creating a diagnostic task for an unknown failed action."""
        mock_uuid.uuid4.return_value.hex = "uuidabc"
        agent = PromptFeedbackLoopAgent(self.mock_bus_instance, self.test_task_list_path, MockLock())
        failed_task = {
            "task_id": "orig_unk_1",
            "action": "DO_WEIRD_STUFF",
            "params": {"level": 9000},
            "status": "FAILED"
        }

        diag_task = agent._create_diagnostic_task(failed_task)

        self.assertEqual(diag_task["task_type"], "diagnose_DO_WEIRD_STUFF_failure")
        self.assertEqual(diag_task["action"], "RUN_TERMINAL_COMMAND")
        # Check params
        params = diag_task["params"]
        self.assertIn("Running default diagnostics", params["command"])
        self.assertIn("pwd", params["command"])
        self.assertIn("ls -alh", params["command"])

    # TODO: Test handle_potential_failure (needs full implementation visible first)

if __name__ == '__main__':
    unittest.main()