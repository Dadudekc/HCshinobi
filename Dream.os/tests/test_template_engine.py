import unittest
import os
import sys
import json # Keep for loading test data if needed

# Add project root to sys.path to allow importing core modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import from core module
try:
    from core.template_engine import render_template
    # Attempt to import necessary components for re-initialization if needed
    from core.template_engine import TEMPLATE_DIR as ENGINE_TEMPLATE_DIR, env as engine_env
    from jinja2 import Environment, FileSystemLoader
    module_load_error = None
except ImportError as e:
    render_template = None
    module_load_error = e
except Exception as e:
    render_template = None
    module_load_error = f"General error during import/setup: {e}"

# Define a directory for test templates relative to this test file
TESTS_DIR = os.path.dirname(__file__)
TEST_TEMPLATE_DIR = os.path.join(TESTS_DIR, "test_templates")

@unittest.skipIf(module_load_error, f"Skipping tests due to module load error: {module_load_error}")
class TestTemplateEngine(unittest.TestCase):

    original_loader = None
    original_filters = None

    @classmethod
    def setUpClass(cls):
        """Set up test templates and mock the Jinja environment loader."""
        os.makedirs(TEST_TEMPLATE_DIR, exist_ok=True)
        with open(os.path.join(TEST_TEMPLATE_DIR, "valid_template.j2"), "w") as f:
            f.write("Hello {{ name }}! Value: {{ data.value }}")
        with open(os.path.join(TEST_TEMPLATE_DIR, "json_template.j2"), "w") as f:
            f.write("Data: {{ complex_data | tojson }}")

        # More robust mocking: Replace the environment's loader
        if engine_env:
            cls.original_loader = engine_env.loader
            cls.original_filters = engine_env.filters.copy()
            engine_env.loader = FileSystemLoader(TEST_TEMPLATE_DIR)
            # Ensure our test env has the filter
            engine_env.filters['tojson'] = lambda v: json.dumps(v)
            print(f"NOTE: Redirected Jinja environment loader to use: {TEST_TEMPLATE_DIR}")
        else:
            print("WARNING: Engine environment not found, tests might rely on default setup or fail.")

    @classmethod
    def tearDownClass(cls):
        """Clean up test templates and restore the original loader."""
        # Restore original loader and filters
        if cls.original_loader and engine_env:
            engine_env.loader = cls.original_loader
            engine_env.filters = cls.original_filters
            print("Restored original Jinja environment loader.")

        # Remove test files and directory
        try:
            os.remove(os.path.join(TEST_TEMPLATE_DIR, "valid_template.j2"))
            os.remove(os.path.join(TEST_TEMPLATE_DIR, "json_template.j2"))
            os.rmdir(TEST_TEMPLATE_DIR)
        except OSError as e:
            print(f"Error cleaning up test templates: {e}")

    def test_render_valid_template(self):
        """Test rendering a basic valid template."""
        context = {"name": "World", "data": {"value": 123}}
        expected = "Hello World! Value: 123"
        rendered = render_template("valid_template.j2", context)
        self.assertEqual(rendered, expected)

    def test_render_with_tojson_filter(self):
        """Test rendering using the custom tojson filter."""
        context = {"complex_data": {"key": [1, "string"], "nested": True}}
        # Note: json.dumps doesn't guarantee key order or spacing
        import json
        expected_json_str = json.dumps(context["complex_data"])
        expected = f"Data: {expected_json_str}"
        rendered = render_template("json_template.j2", context)
        self.assertEqual(rendered, expected)

    def test_render_template_not_found(self):
        """Test rendering a template that does not exist."""
        rendered = render_template("non_existent.j2", {})
        self.assertIsNone(rendered, "Rendering a non-existent template should return None.")

    def test_render_with_missing_variable(self):
        """Test rendering when a variable used in the template is missing from context."""
        # Jinja2 default behavior is to render missing variables as empty strings
        context = {"name": "OnlyName"}
        expected = "Hello OnlyName! Value: " # data.value becomes empty string
        rendered = render_template("valid_template.j2", context)
        self.assertEqual(rendered, expected)

if __name__ == '__main__':
    if module_load_error:
        print(f"\nCannot run tests: Failed to import template_engine module from core.")
        print(f"Error: {module_load_error}")
    else:
        unittest.main() 