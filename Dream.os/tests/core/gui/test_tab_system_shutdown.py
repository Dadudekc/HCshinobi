import unittest
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from datetime import datetime

# --- Add project root to sys.path ---
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent # Adjust as needed
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# ------------------------------------

# Mock dependencies
class MockFeedbackEngine:
    def __init__(self):
        self.logged_events = []

    def log_event(self, event_type, data):
        print(f"MockFeedbackEngine logged: {event_type} - {data}")
        self.logged_events.append((event_type, data))

class MockTab:
    def __init__(self, name="MockTab", state=None, prep_success=True):
        self.name = name
        self._state = state or {"default": "state"}
        self._prep_success = prep_success
        self.prepare_called = False
        self.get_state_called = False
        self.timer = MagicMock()
        self.timer.stop = MagicMock()
        self.refresh_timer = self.timer # Alias for compatibility

    def get_state(self):
        self.get_state_called = True
        print(f"Tab {self.name} get_state called.")
        return self._state

    def prepare_for_shutdown(self):
        self.prepare_called = True
        print(f"Tab {self.name} prepare_for_shutdown called. Success: {self._prep_success}")
        return self._prep_success

# Import the class to be tested
from core.gui.tab_system_shutdown import TabSystemShutdownManager

class TestTabSystemShutdown(unittest.TestCase):

    def setUp(self):
        """Set up mocks and manager instance for each test."""
        self.mock_feedback_engine = MockFeedbackEngine()
        self.test_dir = Path("./temp_shutdown_test")
        self.test_dir.mkdir(exist_ok=True)
        self.state_file = self.test_dir / "tab_states.json"

        self.manager = TabSystemShutdownManager(
            feedback_engine=self.mock_feedback_engine,
            agent_directory=str(self.test_dir)
        )

        # Mock the logger within the shutdown manager module
        self.patcher_logger = patch('core.gui.tab_system_shutdown.logger')
        self.mock_logger = self.patcher_logger.start()

        # Mock datetime to control timestamps if needed (optional)
        # self.patcher_dt = patch('core.gui.tab_system_shutdown.datetime')
        # self.mock_datetime = self.patcher_dt.start()
        # self.mock_datetime.utcnow.return_value = datetime(2023, 1, 1, 12, 0, 0)

        # Mock os.replace for testing atomic write
        self.patcher_os_replace = patch('core.gui.tab_system_shutdown.os.replace')
        self.mock_os_replace = self.patcher_os_replace.start()

    def tearDown(self):
        """Clean up mocks and temporary files."""
        self.patcher_logger.stop()
        self.patcher_os_replace.stop()
        # self.patcher_dt.stop()
        if self.state_file.exists():
            self.state_file.unlink()
        if self.test_dir.exists():
            try:
                # Remove potential temp file as well
                tmp_file = self.state_file.with_suffix(".tmp")
                if tmp_file.exists():
                    tmp_file.unlink()
                os.rmdir(str(self.test_dir))
            except OSError:
                pass

    def test_01_initiate_shutdown_happy_path(self):
        """Test the full shutdown sequence with successful tabs."""
        print("\n--- Test: Shutdown Happy Path ---")
        tab1 = MockTab("Tab1", state={"value": 1})
        tab2 = MockTab("Tab2", state={"value": 2})
        tabs = {"tab1": tab1, "tab2": tab2}

        # Mock the signal emit
        self.manager.shutdown_complete.emit = MagicMock()

        # Run shutdown
        self.manager.initiate_shutdown(tabs)

        # --- Assertions --- 
        # 1. Prepare and Get State called on tabs
        self.assertTrue(tab1.prepare_called, "Tab1 prepare_for_shutdown not called")
        self.assertTrue(tab1.get_state_called, "Tab1 get_state not called")
        self.assertTrue(tab2.prepare_called, "Tab2 prepare_for_shutdown not called")
        self.assertTrue(tab2.get_state_called, "Tab2 get_state not called")

        # 2. State file written correctly
        self.assertTrue(self.state_file.exists(), "State file not created")
        with open(self.state_file, 'r') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, {"tab1": {"value": 1}, "tab2": {"value": 2}})
        self.mock_os_replace.assert_called_once() # Check atomic write was attempted

        # 3. Feedback events logged
        logged_types = [event[0] for event in self.mock_feedback_engine.logged_events]
        self.assertIn("system_shutdown", logged_types, "system_shutdown event not logged")
        self.assertIn("shutdown_ready", logged_types, "shutdown_ready event not logged")

        # 4. Completion signal emitted
        self.manager.shutdown_complete.emit.assert_called_once()
        print("Shutdown happy path test passed.")

    def test_02_shutdown_with_failing_prepare(self):
        """Test shutdown when one tab fails the prepare_for_shutdown step."""
        print("\n--- Test: Shutdown with Failing Prepare ---")
        tab1 = MockTab("Tab1", state={"value": 1}, prep_success=True)
        tab2 = MockTab("Tab2", state={"value": 2}, prep_success=False) # This one fails
        tabs = {"tab1": tab1, "tab2": tab2}

        self.manager.shutdown_complete.emit = MagicMock()
        self.manager.initiate_shutdown(tabs)

        # --- Assertions --- 
        # 1. Prepare called, get_state only called for successful tab
        self.assertTrue(tab1.prepare_called)
        self.assertTrue(tab1.get_state_called)
        self.assertTrue(tab2.prepare_called) # Prepare is still called
        self.assertFalse(tab2.get_state_called, "get_state should not be called if prepare fails")

        # 2. State file should only contain state from the successful tab
        self.assertTrue(self.state_file.exists())
        with open(self.state_file, 'r') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, {"tab1": {"value": 1}})
        self.mock_os_replace.assert_called_once()

        # 3. Warning logged about preparation issue
        self.mock_logger.warning.assert_any_call("Tab 'tab2' reported issues during shutdown preparation.")
        self.mock_logger.warning.assert_any_call("One or more tabs reported issues during shutdown preparation.")

        # 4. Shutdown still completes (logs events, emits signal)
        logged_types = [event[0] for event in self.mock_feedback_engine.logged_events]
        self.assertIn("system_shutdown", logged_types)
        self.assertIn("shutdown_ready", logged_types)
        self.manager.shutdown_complete.emit.assert_called_once()
        print("Shutdown with failing prepare test passed.")

    def test_03_shutdown_persisted_state_error(self):
        """Test shutdown sequence when saving the state file fails."""
        print("\n--- Test: Shutdown with State Persistence Error ---")
        tab1 = MockTab("Tab1", state={"value": 1})
        tabs = {"tab1": tab1}

        # Mock open to raise an error during state file writing
        with patch('builtins.open', side_effect=IOError("Disk full")):
            self.manager.shutdown_complete.emit = MagicMock()
            self.manager._handle_shutdown_error = MagicMock() # Also mock error handler

            self.manager.initiate_shutdown(tabs)

            # --- Assertions --- 
            # 1. Prepare and Get State still called
            self.assertTrue(tab1.prepare_called)
            self.assertTrue(tab1.get_state_called)

            # 2. State file should NOT exist
            self.assertFalse(self.state_file.exists())
            self.mock_os_replace.assert_not_called() # Atomic replace shouldn't happen

            # 3. Shutdown error handler called
            self.manager._handle_shutdown_error.assert_called_once()
            self.assertIsInstance(self.manager._handle_shutdown_error.call_args[0][0], IOError)

            # 4. Completion signal NOT emitted (due to exception)
            self.manager.shutdown_complete.emit.assert_not_called()

            # 5. Critical log occurred
            self.mock_logger.error.assert_any_call(
                "CRITICAL: Error persisting tab states to file: Disk full",
                exc_info=True
            )
            print("Shutdown with persistence error test passed.")

    # TODO: Add test for _handle_shutdown_error logging
    # TODO: Add test for cases where tabs lack get_state or prepare_for_shutdown

if __name__ == '__main__':
    unittest.main() 