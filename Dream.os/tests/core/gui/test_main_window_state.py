# Placeholder for test file creation
# This edit ensures the directory is created if it doesn't exist 

import unittest
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# --- Add project root to sys.path ---
# Assuming this test file is in tests/core/gui
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent # Adjust based on actual structure
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# ------------------------------------

# Mock PyQt classes before importing the main window
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QLabel, QStatusBar

# Define dummy classes for components that MainWindow depends on
class MockTaskManager:
    def get_tasks(self): return []

class MockFeedbackEngine:
    def get_events(self): return []
    def log_event(self, *args, **kwargs): pass

class MockTabManager(QTabWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._tabs = {}

    def add_tab(self, widget, name):
        super().addTab(widget, name)
        self._tabs[name.lower().replace(" ", "_")] = widget

    def widget(self, index):
        return super().widget(index)

    def tabText(self, index):
         # Provide a default name if needed
         return f"Tab {index+1}"

    def count(self):
         return super().count()

    def get_tab_by_name(self, name):
        return self._tabs.get(name)

class MockTab:
    def __init__(self, name="MockTab"):
        self.name = name
        self.state = {"value": "initial"}

    def get_state(self):
        print(f"Getting state for {self.name}: {self.state}")
        return self.state

    def restore_state(self, state):
        print(f"Restoring state for {self.name}: {state}")
        self.state = state

    def prepare_for_shutdown(self):
        print(f"Preparing {self.name} for shutdown")
        return True # Simulate successful preparation

# Now import the class to be tested
from core.gui.main_window import DreamOSMainWindow

# Mock the QTimer class to prevent timers from actually running during tests
@patch('PyQt5.QtCore.QTimer', MagicMock())
class TestMainWindowState(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up QApplication instance for tests."""
        # Need one QApplication instance per test run
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        """Set up a new main window instance and mock dependencies for each test."""
        # Create a temporary directory for test state files
        self.test_dir = Path("./temp_test_state")
        self.test_dir.mkdir(exist_ok=True)
        self.state_file_path = self.test_dir / "tab_states.json"

        # Patch dependencies directly before creating the instance
        with patch('core.gui.main_window.TaskManager', return_value=MockTaskManager()) as MockTM,
             patch('core.gui.main_window.FeedbackEngine', return_value=MockFeedbackEngine()) as MockFE,
             patch('core.gui.main_window.DreamOSTabManager', return_value=MockTabManager()) as MockTBM,
             patch('core.gui.main_window.TabSystemShutdownManager') as MockShutdownMgr: # Keep shutdown manager mocked

            # Create the main window instance
            self.window = DreamOSMainWindow()
            # Override the state file path to use the test directory
            self.window.state_file = self.state_file_path

            # Add some mock tabs to the mocked tab manager
            self.tab1 = MockTab(name="Task Monitor")
            self.tab2 = MockTab(name="Cycle Execution")
            self.window.tab_manager.add_tab(self.tab1, "Task Monitor")
            self.window.tab_manager.add_tab(self.tab2, "Cycle Execution")

            # Mock methods that interact with GUI elements we don't need to test directly here
            self.window.statusBar = MagicMock(return_value=MagicMock(spec=QStatusBar))
            self.window.statusBar().showMessage = MagicMock()
            self.window.status_label = MagicMock(spec=QLabel)
            self.window.task_count_label = MagicMock(spec=QLabel)
            self.window.event_count_label = MagicMock(spec=QLabel)

            # Mock QMessageBox to avoid GUI popups during tests
            self.patcher_msgbox = patch('core.gui.main_window.QMessageBox')
            self.MockMessageBox = self.patcher_msgbox.start()

    def tearDown(self):
        """Clean up after each test."""
        self.patcher_msgbox.stop()
        if self.state_file_path.exists():
            self.state_file_path.unlink()
        if self.test_dir.exists():
            # Be cautious deleting directories, ensure it's the correct one
            try:
                os.rmdir(str(self.test_dir)) # Use os.rmdir as Path.rmdir might fail if not empty
            except OSError:
                 pass # Ignore if removal fails (e.g., other temp files)

    def test_01_save_state_creates_file(self):
        """Test that _save_state creates the state file with correct content."""
        print("\n--- Test: Save State Creates File ---")
        # Set some state on mock tabs
        self.tab1.state = {"filter": "running", "selected": "task123"}
        self.tab2.state = {"template": "templateA", "cycles": 5}

        # Trigger save state
        self.window._save_state()

        # Assertions
        self.assertTrue(self.state_file_path.exists(), "State file was not created.")
        with open(self.state_file_path, 'r') as f:
            saved_data = json.load(f)

        expected_data = {
            "task_monitor": {"filter": "running", "selected": "task123"},
            "cycle_execution": {"template": "templateA", "cycles": 5}
        }
        self.assertEqual(saved_data, expected_data, "Saved state content does not match expected.")
        print("Save state test passed.")

    def test_02_load_state_restores_tabs(self):
        """Test that _load_state correctly calls restore_state on tabs."""
        print("\n--- Test: Load State Restores Tabs ---")
        # Prepare a state file
        initial_state = {
            "task_monitor": {"filter": "completed", "selected": "task456"},
            "cycle_execution": {"template": "templateB", "cycles": 10}
        }
        with open(self.state_file_path, 'w') as f:
            json.dump(initial_state, f)

        # Mock the restore_state methods to check if they are called
        self.tab1.restore_state = MagicMock()
        self.tab2.restore_state = MagicMock()

        # Trigger load state
        self.window._load_state()

        # Assertions
        self.tab1.restore_state.assert_called_once_with(initial_state["task_monitor"])
        self.tab2.restore_state.assert_called_once_with(initial_state["cycle_execution"])
        self.window.statusBar().showMessage.assert_called_with("Restored state for 2 tabs.", 5000)
        print("Load state test passed.")

    def test_03_load_state_no_file(self):
        """Test that _load_state handles non-existent state file gracefully."""
        print("\n--- Test: Load State No File ---")
        # Ensure file doesn't exist
        if self.state_file_path.exists():
            self.state_file_path.unlink()

        self.tab1.restore_state = MagicMock()
        self.tab2.restore_state = MagicMock()

        # Trigger load state
        self.window._load_state()

        # Assertions
        self.tab1.restore_state.assert_not_called()
        self.tab2.restore_state.assert_not_called()
        # Check that no error message was shown
        self.MockMessageBox.warning.assert_not_called()
        print("Load state (no file) test passed.")

    def test_04_load_state_corrupt_file(self):
        """Test that _load_state handles corrupt JSON file."""
        print("\n--- Test: Load State Corrupt File ---")
        # Create a corrupt state file
        with open(self.state_file_path, 'w') as f:
            f.write("this is not json{")

        self.tab1.restore_state = MagicMock()
        self.tab2.restore_state = MagicMock()

        # Trigger load state
        self.window._load_state()

        # Assertions
        self.tab1.restore_state.assert_not_called()
        self.tab2.restore_state.assert_not_called()
        # Check that a warning was shown
        self.MockMessageBox.warning.assert_called_once()
        self.assertTrue("Invalid format" in self.MockMessageBox.warning.call_args[0][1])
        print("Load state (corrupt file) test passed.")

    # TODO: Add tests for manual_save_state and auto_save_state (might need timer mocking)
    # TODO: Add tests for shutdown sequence integration if possible

if __name__ == '__main__':
    unittest.main() 