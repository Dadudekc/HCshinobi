import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
from dreamforge.core.template_engine import TemplateEngine, TemplateNotFound, TemplateRenderError, log_event

class TestTemplateEngine(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.engine = TemplateEngine()
        self.test_template = {
            "name": "test_template",
            "content": "Hello, {{ name }}!",
            "variables": ["name"]
        }
        log_event("TEST_ADDED", "TestTemplateEngine", {"test_suite": "TemplateEngine"})

    def tearDown(self):
        """Clean up test artifacts."""
        if hasattr(self.engine, '_template_cache'):
            self.engine._template_cache.clear()

    @patch('dreamforge.core.template_engine.log_event')
    def test_render_valid_template(self, mock_log_event):
        """Test successful template rendering."""
        with patch.object(self.engine, '_load_template', return_value=self.test_template):
            result = self.engine.render("test_template", {"name": "World"})
            self.assertEqual(result, "Hello, World!")
            mock_log_event.assert_called_with(
                "TEMPLATE_RENDERED",
                "template_engine",
                {"template": "test_template", "variables": ["name"]}
            )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_render_valid_template"})

    @patch('dreamforge.core.template_engine.log_event')
    def test_render_missing_template(self, mock_log_event):
        """Test rendering with non-existent template."""
        with patch.object(self.engine, '_load_template', side_effect=TemplateNotFound("missing")):
            with self.assertRaises(TemplateNotFound):
                self.engine.render("missing", {})
            mock_log_event.assert_called_with(
                "TEMPLATE_NOT_FOUND",
                "template_engine",
                {"template": "missing"}
            )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_render_missing_template"})

    @patch('dreamforge.core.template_engine.log_event')
    def test_render_missing_variables(self, mock_log_event):
        """Test rendering with missing required variables."""
        with patch.object(self.engine, '_load_template', return_value=self.test_template):
            with self.assertRaises(TemplateRenderError):
                self.engine.render("test_template", {})
            mock_log_event.assert_called_with(
                "TEMPLATE_RENDER_ERROR",
                "template_engine",
                {"template": "test_template", "error": "Missing required variables: name"}
            )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_render_missing_variables"})

    @patch('dreamforge.core.template_engine.log_event')
    def test_template_caching(self, mock_log_event):
        """Test template caching mechanism."""
        load_count = 0
        def mock_load(template_name):
            nonlocal load_count
            load_count += 1
            return self.test_template

        with patch.object(self.engine, '_load_template', side_effect=mock_load):
            # First render should load template
            self.engine.render("test_template", {"name": "First"})
            # Second render should use cache
            self.engine.render("test_template", {"name": "Second"})
            
            self.assertEqual(load_count, 1)
            mock_log_event.assert_any_call(
                "TEMPLATE_CACHED",
                "template_engine",
                {"template": "test_template"}
            )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_template_caching"})

    @patch('dreamforge.core.template_engine.log_event')
    def test_template_reload(self, mock_log_event):
        """Test template reloading."""
        templates = [
            {"name": "test_template", "content": "Version 1", "variables": []},
            {"name": "test_template", "content": "Version 2", "variables": []}
        ]
        template_iter = iter(templates)
        
        with patch.object(self.engine, '_load_template', side_effect=lambda _: next(template_iter)):
            result1 = self.engine.render("test_template", {})
            self.assertEqual(result1, "Version 1")
            
            self.engine.reload_template("test_template")
            result2 = self.engine.render("test_template", {})
            self.assertEqual(result2, "Version 2")
            
            mock_log_event.assert_any_call(
                "TEMPLATE_RELOADED",
                "template_engine",
                {"template": "test_template"}
            )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_template_reload"})

    @patch('dreamforge.core.template_engine.log_event')
    def test_nested_template_rendering(self, mock_log_event):
        """Test rendering of nested templates."""
        parent_template = {
            "name": "parent",
            "content": "Parent: {% include 'child' %}",
            "variables": ["child_var"]
        }
        child_template = {
            "name": "child",
            "content": "Child: {{ child_var }}",
            "variables": ["child_var"]
        }
        
        def mock_load(template_name):
            return parent_template if template_name == "parent" else child_template
            
        with patch.object(self.engine, '_load_template', side_effect=mock_load):
            result = self.engine.render("parent", {"child_var": "test"})
            self.assertEqual(result, "Parent: Child: test")
            mock_log_event.assert_any_call(
                "TEMPLATE_NESTED_RENDER",
                "template_engine",
                {"parent": "parent", "child": "child"}
            )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_nested_template_rendering"})

    @patch('dreamforge.core.template_engine.log_event')
    def test_template_inheritance(self, mock_log_event):
        """Test template inheritance with blocks."""
        base_template = {
            "name": "base",
            "content": "{% block header %}Base Header{% endblock %} - {% block content %}{% endblock %}",
            "variables": ["title"]
        }
        child_template = {
            "name": "child",
            "content": "{% extends 'base' %}{% block content %}{{ title }}{% endblock %}",
            "variables": ["title"]
        }
        
        def mock_load(template_name):
            return base_template if template_name == "base" else child_template
            
        with patch.object(self.engine, '_load_template', side_effect=mock_load):
            result = self.engine.render("child", {"title": "Test Content"})
            self.assertEqual(result, "Base Header - Test Content")
            mock_log_event.assert_any_call(
                "TEMPLATE_INHERITANCE_RENDER",
                "template_engine",
                {"child": "child", "parent": "base"}
            )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_template_inheritance"})

    @patch('dreamforge.core.template_engine.log_event')
    def test_template_filters(self, mock_log_event):
        """Test template filters and custom filter registration."""
        template = {
            "name": "filter_test",
            "content": "{{ text|upper|trim }}",
            "variables": ["text"]
        }
        
        def custom_trim(value):
            return value.strip()
            
        with patch.object(self.engine, '_load_template', return_value=template):
            self.engine.register_filter("trim", custom_trim)
            result = self.engine.render("filter_test", {"text": " hello "})
            self.assertEqual(result, "HELLO")
            mock_log_event.assert_any_call(
                "TEMPLATE_FILTER_APPLIED",
                "template_engine",
                {"template": "filter_test", "filters": ["upper", "trim"]}
            )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_template_filters"})

    @patch('dreamforge.core.template_engine.log_event')
    def test_template_error_handling(self, mock_log_event):
        """Test template error handling for various error conditions."""
        error_cases = [
            {
                "template": {"name": "syntax_error", "content": "{% invalid %}"},
                "vars": {},
                "error": "TemplateSyntaxError"
            },
            {
                "template": {"name": "type_error", "content": "{{ number + 'string' }}"},
                "vars": {"number": 42},
                "error": "TypeError"
            }
        ]
        
        for case in error_cases:
            with patch.object(self.engine, '_load_template', return_value=case["template"]):
                with self.assertRaises(TemplateRenderError):
                    self.engine.render(case["template"]["name"], case["vars"])
                mock_log_event.assert_any_call(
                    "TEMPLATE_RENDER_ERROR",
                    "template_engine",
                    {
                        "template": case["template"]["name"],
                        "error_type": case["error"]
                    }
                )
        log_event("TEST_PASSED", "TestTemplateEngine", {"test": "test_template_error_handling"})

if __name__ == "__main__":
    unittest.main() 