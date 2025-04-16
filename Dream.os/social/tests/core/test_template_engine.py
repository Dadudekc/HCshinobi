import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from jinja2 import TemplateNotFound, TemplateSyntaxError

# --- Add project root to sys.path ---
# This assumes the script is in tests/core/
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Module to test
from core.template_engine import render_template, template_env
from utils.logging_utils import log_event

@patch('core.template_engine.print')
class TestRenderTemplateFunction(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory for dummy templates."""
        # Create a temporary directory structure that mimics project root for FileSystemLoader
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root_mock = self.temp_dir.name
        self.social_templates_dir = os.path.join(self.project_root_mock, 'social')
        os.makedirs(self.social_templates_dir)
        
        # Create dummy social templates
        self.generic_event_path = os.path.join(self.social_templates_dir, 'generic_event.j2')
        self.proposal_update_path = os.path.join(self.social_templates_dir, 'proposal_update.j2')
        self.syntax_error_path = os.path.join(self.social_templates_dir, 'syntax_error.j2')
        self.complex_template_path = os.path.join(self.social_templates_dir, 'complex.j2')

        with open(self.generic_event_path, 'w') as f:
            f.write("Generic Event: {{ event_type }}. Details: {{ details }}")
        with open(self.proposal_update_path, 'w') as f:
            f.write("Proposal [{{ proposal_id }}] status changed to {{ status_update }} by {{ agent_id }}.")
        with open(self.syntax_error_path, 'w') as f:
            f.write("This has a {{ syntax_error }") # Missing closing braces
        with open(self.complex_template_path, 'w') as f:
            f.write("""{% for item in items %}
                {{ item.name }}: {{ item.value }}
                {% if item.details %}
                Details: {{ item.details | default('N/A') }}
                {% endif %}
            {% endfor %}""")

        # Patch the FileSystemLoader
        self.patcher = patch('core.template_engine.project_root', self.project_root_mock)
        self.mock_proj_root = self.patcher.start()
        
        # Initialize test environment
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            test_loader = FileSystemLoader(self.project_root_mock, followlinks=True)
            self.test_env = Environment(
                loader=test_loader,
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            self.env_patcher = patch('core.template_engine.template_env', self.test_env)
            self.mock_env = self.env_patcher.start()
            self.env_setup_ok = True
        except Exception as e:
            print(f"!!! Test Setup Warning: Could not patch template_env directly: {e}")
            self.env_setup_ok = False
            self.env_patcher = None

    def tearDown(self):
        """Clean up the temporary directory and stop patches."""
        self.patcher.stop()
        if self.env_patcher:
            self.env_patcher.stop()
        self.temp_dir.cleanup()

    def test_render_generic_event_success(self, mock_print):
        """Test rendering the generic_event template successfully."""
        if not self.env_setup_ok:
            self.skipTest("Template env patching failed")
        context = {"event_type": "TESTING", "details": "All systems nominal."}
        expected_output = "Generic Event: TESTING. Details: All systems nominal."
        result = render_template('social/generic_event.j2', context)
        self.assertEqual(result, expected_output)
        mock_print.assert_any_call(f"[TemplateEngine] Successfully rendered template 'social/generic_event.j2'")
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_generic_event_success"})

    def test_render_proposal_update_success(self, mock_print):
        """Test rendering the proposal_update template successfully."""
        if not self.env_setup_ok:
            self.skipTest("Template env patching failed")
        context = {"proposal_id": "P123", "status_update": "Passed", "agent_id": "Supervisor"}
        expected_output = "Proposal [P123] status changed to Passed by Supervisor."
        result = render_template('social/proposal_update.j2', context)
        self.assertEqual(result, expected_output)
        mock_print.assert_any_call(f"[TemplateEngine] Successfully rendered template 'social/proposal_update.j2'")
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_proposal_update_success"})

    def test_render_template_not_found(self, mock_print):
        """Test rendering a template that does not exist."""
        if not self.env_setup_ok:
            self.skipTest("Template env patching failed")
        context = {"data": 1}
        result = render_template('social/nonexistent_template.j2', context)
        self.assertIsNone(result)
        mock_print.assert_any_call("[TemplateEngine] Error rendering template: Template 'social/nonexistent_template.j2' not found.")
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_template_not_found"})

    def test_render_template_syntax_error(self, mock_print):
        """Test rendering a template with a syntax error."""
        if not self.env_setup_ok:
            self.skipTest("Template env patching failed")
        context = {"syntax_error": "test"}
        result = render_template('social/syntax_error.j2', context)
        self.assertIsNone(result)
        found_log = False
        for call_args, _ in mock_print.call_args_list:
            if "Syntax error at line" in call_args[0]:
                found_log = True
                break
        self.assertTrue(found_log, "Expected syntax error log message not found")
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_template_syntax_error"})

    @patch('core.template_engine.template_env', None)
    def test_render_engine_unavailable(self, mock_print):
        """Test rendering when the template_env is None."""
        context = {"a": 1}
        result = render_template('social/generic_event.j2', context)
        self.assertIsNone(result)
        mock_print.assert_any_call("[TemplateEngine] Error rendering 'social/generic_event.j2': Environment not available.")
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_engine_unavailable"})

    def test_render_complex_template(self, mock_print):
        """Test rendering a complex template with loops and conditionals."""
        if not self.env_setup_ok:
            self.skipTest("Template env patching failed")
        context = {
            "items": [
                {"name": "Item1", "value": 100, "details": "Important"},
                {"name": "Item2", "value": 200},
                {"name": "Item3", "value": 300, "details": "Critical"}
            ]
        }
        result = render_template('social/complex.j2', context)
        self.assertIsNotNone(result)
        self.assertIn("Item1: 100", result)
        self.assertIn("Details: Important", result)
        self.assertIn("Item2: 200", result)
        self.assertNotIn("Details: N/A", result)  # Item2 has no details
        self.assertIn("Item3: 300", result)
        self.assertIn("Details: Critical", result)
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_complex_template"})

    def test_render_with_undefined_variables(self, mock_print):
        """Test rendering with undefined template variables."""
        if not self.env_setup_ok:
            self.skipTest("Template env patching failed")
        context = {}  # Empty context
        result = render_template('social/generic_event.j2', context)
        self.assertIsNotNone(result)
        self.assertIn("Generic Event:", result)
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_with_undefined_variables"})

    def test_render_with_custom_filters(self, mock_print):
        """Test rendering with custom template filters."""
        if not self.env_setup_ok:
            self.skipTest("Template env patching failed")
        
        def custom_upper(value):
            return str(value).upper()
        
        self.test_env.filters['custom_upper'] = custom_upper
        
        with open(os.path.join(self.social_templates_dir, 'filter_test.j2'), 'w') as f:
            f.write("{{ text | custom_upper }}")
        
        context = {"text": "test"}
        result = render_template('social/filter_test.j2', context)
        self.assertEqual(result, "TEST")
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_with_custom_filters"})

    @patch('core.template_engine.template_env')
    def test_render_with_general_exception(self, mock_env, mock_print):
        """Test handling of general exceptions during rendering."""
        mock_template = MagicMock()
        mock_template.render.side_effect = Exception("Unexpected error")
        mock_env.get_template.return_value = mock_template
        
        result = render_template('social/generic_event.j2', {})
        self.assertIsNone(result)
        mock_print.assert_any_call(unittest.mock.ANY)
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_render_with_general_exception"})

if __name__ == '__main__':
    unittest.main() 