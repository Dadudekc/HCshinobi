import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json

# Add project root to sys.path to allow importing core modules
script_dir = os.path.dirname(__file__) # tests/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # D:/Dream.os/
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the service to test
try:
    # Import specific functions if testing them directly
    from core.prompt_staging_service import render_prompt, stage_prompt_for_cursor, fetch_cursor_response
    # Import dependencies that might need mocking
    import core.memory.supervisor_memory
    import core.template_engine
    import core.memory.governance_memory_engine
    import tools.chat_cursor_bridge
    module_load_error = None
except ImportError as e:
    render_prompt = stage_prompt_for_cursor = fetch_cursor_response = None
    module_load_error = e
except Exception as e:
    render_prompt = stage_prompt_for_cursor = fetch_cursor_response = None
    module_load_error = f"General error during import/setup: {e}"


# Define a directory for test templates relative to this test file
TESTS_DIR = os.path.dirname(__file__)
TEST_TEMPLATE_DIR_PSS = os.path.join(TESTS_DIR, "test_templates_pss") # Separate dir for PSS tests

@unittest.skipIf(module_load_error, f"Skipping tests due to module load error: {module_load_error}")
class TestPromptStagingService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up test templates for PSS."""
        os.makedirs(TEST_TEMPLATE_DIR_PSS, exist_ok=True)
        # Template to check state and scan injection
        with open(os.path.join(TEST_TEMPLATE_DIR_PSS, "state_scan_test.j2"), "w") as f:
            f.write("User: {{ user }}\nFocus: {{ supervisor_state.current_focus.purpose }}\nScan Files: {{ project_scan.summary.total_files }}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test templates."""
        try:
            os.remove(os.path.join(TEST_TEMPLATE_DIR_PSS, "state_scan_test.j2"))
            os.rmdir(TEST_TEMPLATE_DIR_PSS)
        except OSError as e:
            print(f"Error cleaning up PSS test templates: {e}")

    # Patch dependencies used by render_prompt and stage_prompt_for_cursor
    @patch('core.prompt_staging_service.load_state') # Mock supervisor state loading
    @patch('core.prompt_staging_service._load_project_analysis') # Mock project analysis loading
    @patch('core.template_engine.default_template_engine.render') # Mock the actual render call
    @patch('core.prompt_staging_service.log_event') # Mock logging
    def setUp(self, mock_log_event, mock_render, mock_load_analysis, mock_load_state):
        """Set up mocks for each test."""
        self.mock_log_event = mock_log_event
        self.mock_render = mock_render
        self.mock_load_analysis = mock_load_analysis
        self.mock_load_state = mock_load_state
        
        # Configure default mock return values
        self.mock_supervisor_state = {
            "last_updated": "now",
            "current_focus": {"purpose": "Test Focus", "context_snippet": "Testing..."},
            "active_goals": ["Test Goal 1"],
            "agent_states": {},
            "task_assignments": {},
            "system_notes": []
        }
        self.mock_load_state.return_value = self.mock_supervisor_state
        
        self.mock_project_analysis = {
            "error": None, # Indicate success
            "files": {"test.py": {}},
            "summary": {"total_files": 1}
        }
        self.mock_load_analysis.return_value = self.mock_project_analysis
        
        # Make the mock render return something simple by default
        self.mock_render.return_value = "Mock Rendered Output"

    def test_render_prompt_injects_state_and_scan(self):
        """Test that render_prompt correctly injects state and scan data into context."""
        user_context = {"user": "Test User"}
        template_name = "some_template.j2"
        
        # Call the function under test
        render_prompt(template_name, user_context)
        
        # Verify mocks
        self.mock_load_state.assert_called_once()
        self.mock_load_analysis.assert_called_once()
        self.mock_render.assert_called_once()
        
        # Check the context passed to the actual render function
        call_args, _ = self.mock_render.call_args
        passed_template_name = call_args[0]
        passed_context = call_args[1]
        
        self.assertEqual(passed_template_name, template_name)
        self.assertEqual(passed_context['user'], "Test User")
        self.assertEqual(passed_context['supervisor_state'], self.mock_supervisor_state)
        self.assertEqual(passed_context['project_scan'], self.mock_project_analysis)
        
        # Verify logging (optional, but good practice)
        self.mock_log_event.assert_any_call("PROMPT_RENDERED", unittest.mock.ANY)

    @patch('core.prompt_staging_service.write_to_cursor_input')
    def test_stage_prompt_for_cursor_success(self, mock_write_bridge):
        """Test stage_prompt_for_cursor successfully renders and writes."""
        # Mock the bridge function to simulate successful write
        mock_write_bridge.return_value = True
        # Mock render_prompt implicitly via setUp mocks, but we can check its call
        # Or we can mock it directly here too if we want specific return value for staging
        # self.mock_render.return_value = "Rendered for Staging"

        user_context = {"user": "Staging User"}
        template_name = "stage_test.j2"

        success = stage_prompt_for_cursor(template_name, user_context)

        self.assertTrue(success)
        # Verify render was called (implicitly via setUp mocks ensuring context injection)
        self.mock_render.assert_called_once()
        call_args, _ = self.mock_render.call_args
        passed_context = call_args[1]
        self.assertEqual(passed_context['user'], "Staging User")
        self.assertIn('supervisor_state', passed_context)
        self.assertIn('project_scan', passed_context)
        
        # Verify the bridge write function was called with the rendered output
        mock_write_bridge.assert_called_once_with(self.mock_render.return_value)
        # Verify logging
        self.mock_log_event.assert_any_call("PROMPT_STAGED", unittest.mock.ANY)

    @patch('core.prompt_staging_service.write_to_cursor_input')
    def test_stage_prompt_for_cursor_render_fails(self, mock_write_bridge):
        """Test stage_prompt_for_cursor when render_prompt fails."""
        # Make the mock render function return None to simulate failure
        self.mock_render.return_value = None
        mock_write_bridge.return_value = True # Write should not be called

        user_context = {"user": "Fail Render"}
        template_name = "fail_render.j2"

        success = stage_prompt_for_cursor(template_name, user_context)

        self.assertFalse(success)
        self.mock_render.assert_called_once() # Render was still attempted
        mock_write_bridge.assert_not_called() # Bridge write should NOT be called
        # Check appropriate error log? render_prompt logs failure, stage might log abort?
        # Currently render_prompt logs PROMPT_RENDER_FAILED
        # stage_prompt_for_cursor doesn't add another log on render fail
        # So check log from render_prompt
        self.mock_log_event.assert_any_call("PROMPT_RENDER_FAILED", unittest.mock.ANY)

    @patch('core.prompt_staging_service.read_from_cursor_output')
    def test_fetch_cursor_response_success(self, mock_read_bridge):
        """Test fetching a valid JSON response from the bridge."""
        mock_response_data = {"status": "ok", "result": "some data"}
        mock_read_bridge.return_value = mock_response_data

        response = fetch_cursor_response()

        self.assertEqual(response, mock_response_data)
        mock_read_bridge.assert_called_once()
        self.mock_log_event.assert_any_call("RESPONSE_FETCHED", unittest.mock.ANY)

    @patch('core.prompt_staging_service.read_from_cursor_output')
    def test_fetch_cursor_response_no_file(self, mock_read_bridge):
        """Test fetching when the bridge returns None (e.g., file not found)."""
        mock_read_bridge.return_value = None

        response = fetch_cursor_response()

        self.assertIsNone(response)
        mock_read_bridge.assert_called_once()
        self.mock_log_event.assert_any_call("RESPONSE_FETCH_FAILED", unittest.mock.ANY)

    @patch('core.prompt_staging_service.read_from_cursor_output')
    def test_fetch_cursor_response_invalid_json(self, mock_read_bridge):
        """Test fetching when the bridge read works but returns invalid JSON.
           (Assuming read_from_cursor_output handles JSON errors and returns None)"""
        # Configure the mock bridge function to return None (as if JSON parsing failed)
        mock_read_bridge.return_value = None 
        
        # Simulate the scenario where the bridge function itself would have tried 
        # and failed to parse JSON, returning None.
        
        response = fetch_cursor_response()

        self.assertIsNone(response)
        mock_read_bridge.assert_called_once() # Bridge was still called
        self.mock_log_event.assert_any_call("RESPONSE_FETCH_FAILED", unittest.mock.ANY)

    # --- Add more tests here ---

if __name__ == '__main__':
    if module_load_error:
        print(f"\nCannot run tests: Failed to import PSS module or dependencies from core.")
        print(f"Error: {module_load_error}")
    else:
        unittest.main() 