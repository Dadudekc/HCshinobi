import unittest
import os
import sys
from unittest.mock import patch, MagicMock, ANY

# --- Add project root to sys.path ---
# This assumes the script is in core/
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Modules to test
from core import prompt_staging_service

# Default state structure used on load failure
DEFAULT_EMPTY_STATE = {"error": "Failed to load", "current_focus": {}, "active_goals": [], "agent_states": {}, "task_assignments": {}, "system_notes": []}
DEFAULT_EMPTY_ANALYSIS = {"error": "Analysis unavailable", "files": {}, "summary": {}}


class TestPromptStagingServiceRender(unittest.TestCase):

    @patch('core.prompt_staging_service.log_event', MagicMock()) # Mock logging
    @patch('core.prompt_staging_service._load_project_analysis') # Mock project scan loading
    @patch('core.prompt_staging_service.load_state') # Mock supervisor state loading
    @patch('core.prompt_staging_service.template_engine') # Mock template engine
    def test_render_prompt_success(self, mock_template_engine, mock_load_state, mock_load_analysis):
        """Test successful rendering with valid state and analysis."""
        # Arrange Mocks
        mock_template_engine.render.return_value = "Rendered Prompt Text"
        mock_template_engine.jinja_env = True # Simulate available env
        mock_load_state.return_value = {"active_goals": ["goal1"], "current_focus": {"purpose": "testing"}}
        mock_load_analysis.return_value = {"summary": {"total_files": 5}}
        
        test_template = "test.j2"
        test_context = {"user_var": "value"}
        
        # Act
        result = prompt_staging_service.render_prompt(test_template, test_context)

        # Assert
        self.assertEqual(result, "Rendered Prompt Text")
        mock_load_state.assert_called_once()
        mock_load_analysis.assert_called_once()
        
        # Assert context passed to render contains original context, state, and scan
        expected_render_context = {
            "user_var": "value",
            "supervisor_state": {"active_goals": ["goal1"], "current_focus": {"purpose": "testing"}},
            "project_scan": {"summary": {"total_files": 5}}
        }
        mock_template_engine.render.assert_called_once_with(test_template, expected_render_context)
        prompt_staging_service.log_event.assert_any_call("PROMPT_RENDERED", ANY)


    @patch('core.prompt_staging_service.log_event', MagicMock())
    @patch('core.prompt_staging_service._load_project_analysis')
    @patch('core.prompt_staging_service.load_state')
    @patch('core.prompt_staging_service.template_engine')
    def test_render_prompt_state_load_failure(self, mock_template_engine, mock_load_state, mock_load_analysis):
        """Test rendering when supervisor state loading fails."""
        # Arrange Mocks
        mock_template_engine.render.return_value = "Rendered With Default State"
        mock_template_engine.jinja_env = True
        mock_load_state.return_value = None # Simulate failure
        mock_load_analysis.return_value = {"summary": {"total_files": 1}} # Analysis still loads

        test_template = "test_fail_state.j2"
        test_context = {"data": "abc"}

        # Act
        result = prompt_staging_service.render_prompt(test_template, test_context)

        # Assert
        self.assertEqual(result, "Rendered With Default State")
        mock_load_state.assert_called_once()
        mock_load_analysis.assert_called_once()
        
        # Assert context passed uses the default empty state structure
        expected_render_context = {
            "data": "abc",
            "supervisor_state": DEFAULT_EMPTY_STATE,
            "project_scan": {"summary": {"total_files": 1}}
        }
        mock_template_engine.render.assert_called_once_with(test_template, expected_render_context)
        prompt_staging_service.log_event.assert_any_call("SUPERVISOR_STATE_LOAD_FAILED", ANY)
        prompt_staging_service.log_event.assert_any_call("PROMPT_RENDERED", ANY) # Should still count as rendered


    @patch('core.prompt_staging_service.log_event', MagicMock())
    @patch('core.prompt_staging_service._load_project_analysis')
    @patch('core.prompt_staging_service.load_state')
    @patch('core.prompt_staging_service.template_engine')
    def test_render_prompt_analysis_load_failure(self, mock_template_engine, mock_load_state, mock_load_analysis):
        """Test rendering when project analysis loading fails."""
        # Arrange Mocks
        mock_template_engine.render.return_value = "Rendered With Default Analysis"
        mock_template_engine.jinja_env = True
        mock_load_state.return_value = {"active_goals": ["ok"]} # State loads ok
        mock_load_analysis.return_value = DEFAULT_EMPTY_ANALYSIS # Simulate failure

        test_template = "test_fail_analysis.j2"
        test_context = {"param": "x"}

        # Act
        result = prompt_staging_service.render_prompt(test_template, test_context)

        # Assert
        self.assertEqual(result, "Rendered With Default Analysis")
        mock_load_state.assert_called_once()
        mock_load_analysis.assert_called_once()

        # Assert context passed uses the default analysis structure
        expected_render_context = {
            "param": "x",
            "supervisor_state": {"active_goals": ["ok"]},
            "project_scan": DEFAULT_EMPTY_ANALYSIS
        }
        mock_template_engine.render.assert_called_once_with(test_template, expected_render_context)
        prompt_staging_service.log_event.assert_any_call("PROMPT_RENDERED", ANY)


    @patch('core.prompt_staging_service.log_event', MagicMock())
    @patch('core.prompt_staging_service.template_engine')
    def test_render_prompt_engine_unavailable(self, mock_template_engine):
        """Test rendering when the template engine itself is unavailable."""
        # Arrange Mocks
        mock_template_engine.jinja_env = None # Simulate unavailable env
        # load_state and _load_project_analysis should not be called

        # Act
        result = prompt_staging_service.render_prompt("any.j2", {"a": 1})

        # Assert
        self.assertIsNone(result)
        prompt_staging_service.log_event.assert_called_once_with(
            "PROMPT_RENDER_FAILED", 
            {"template": "any.j2", "error": "Template Engine unavailable"}
        )


    @patch('core.prompt_staging_service.log_event', MagicMock())
    @patch('core.prompt_staging_service._load_project_analysis')
    @patch('core.prompt_staging_service.load_state')
    @patch('core.prompt_staging_service.template_engine')
    def test_render_prompt_render_itself_fails(self, mock_template_engine, mock_load_state, mock_load_analysis):
        """Test rendering when template_engine.render returns None."""
        # Arrange Mocks
        mock_template_engine.render.return_value = None # Simulate render failure
        mock_template_engine.jinja_env = True
        mock_load_state.return_value = {"current_focus": {}}
        mock_load_analysis.return_value = {"summary": {}}

        # Act
        result = prompt_staging_service.render_prompt("fail.j2", {"b": 2})

        # Assert
        self.assertIsNone(result)
        mock_template_engine.render.assert_called_once() # Verify it was called
        prompt_staging_service.log_event.assert_any_call(
             "PROMPT_RENDER_FAILED", 
             {
                "template": "fail.j2", 
                "error": "Rendering failed in TemplateEngine",
                "state_included": True,
                "scan_included": True 
             }
        )

# TODO: Add tests for stage_prompt_for_cursor and fetch_cursor_response if needed separately

if __name__ == '__main__':
    unittest.main() 