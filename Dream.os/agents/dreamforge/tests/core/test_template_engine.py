"""Tests for template engine module."""
import pytest
import os
from unittest.mock import patch, mock_open
from jinja2 import TemplateNotFound, TemplateSyntaxError
from dreamforge.core.template_engine import TemplateEngine
from dreamforge.core.memory.governance_memory_engine import log_event

@pytest.fixture
def template_engine():
    """Create a template engine instance for testing."""
    with patch('dreamforge.core.template_engine.config') as mock_config:
        mock_config.TEMPLATE_DIR = "/templates"
        engine = TemplateEngine()
        log_event("TEST_ADDED", "TestTemplateEngine", {"test": "template_engine_fixture"})
        return engine

def test_template_engine_initialization(template_engine):
    """Test template engine initialization."""
    assert template_engine.env is not None
    assert template_engine.template_dir == "/templates"
    log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_template_engine_initialization"})

def test_render_valid_template(template_engine):
    """Test rendering a valid template."""
    template_content = "Hello {{ name }}!"
    context = {"name": "World"}
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            result = template_engine.render("test.j2", context)
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_valid_template"})
            
            assert result == "Hello World!"

def test_render_template_with_filters(template_engine):
    """Test rendering template with custom filters."""
    template_content = "{{ text | uppercase }}"
    context = {"text": "hello"}
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            result = template_engine.render("test.j2", context)
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_template_with_filters"})
            
            assert result == "HELLO"

def test_render_template_with_includes(template_engine):
    """Test rendering template with includes."""
    main_template = "{% include 'header.j2' %}\nContent\n{% include 'footer.j2' %}"
    header_template = "Header"
    footer_template = "Footer"
    
    def mock_open_wrapper(filename, *args, **kwargs):
        content_map = {
            "/templates/main.j2": main_template,
            "/templates/header.j2": header_template,
            "/templates/footer.j2": footer_template
        }
        return mock_open(read_data=content_map[filename])()
    
    with patch('builtins.open', side_effect=mock_open_wrapper):
        with patch('os.path.exists', return_value=True):
            result = template_engine.render("main.j2", {})
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_template_with_includes"})
            
            assert "Header" in result
            assert "Content" in result
            assert "Footer" in result

def test_render_template_with_loops(template_engine):
    """Test rendering template with loops."""
    template_content = """{% for item in items %}
- {{ item }}
{% endfor %}"""
    context = {"items": ["a", "b", "c"]}
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            result = template_engine.render("test.j2", context)
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_template_with_loops"})
            
            assert "- a" in result
            assert "- b" in result
            assert "- c" in result

def test_render_template_with_conditionals(template_engine):
    """Test rendering template with conditional logic."""
    template_content = """{% if show_header %}Header{% endif %}
Content
{% if show_footer %}Footer{% endif %}"""
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            # Test with both true
            result = template_engine.render("test.j2", {"show_header": True, "show_footer": True})
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_template_with_conditionals"})
            
            assert "Header" in result
            assert "Content" in result
            assert "Footer" in result
            
            # Test with both false
            result = template_engine.render("test.j2", {"show_header": False, "show_footer": False})
            assert "Header" not in result
            assert "Content" in result
            assert "Footer" not in result

def test_render_missing_template(template_engine):
    """Test handling of missing template file."""
    with patch('os.path.exists', return_value=False):
        with pytest.raises(TemplateNotFound):
            template_engine.render("missing.j2", {})
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_missing_template"})

def test_render_invalid_template_syntax(template_engine):
    """Test handling of template with invalid syntax."""
    template_content = "{% invalid syntax %}"
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            with pytest.raises(TemplateSyntaxError):
                template_engine.render("invalid.j2", {})
                log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_invalid_template_syntax"})

def test_render_with_undefined_variable(template_engine):
    """Test handling of undefined variables in template."""
    template_content = "{{ undefined_var }}"
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            result = template_engine.render("test.j2", {})
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_with_undefined_variable"})
            
            assert result == ""  # Default behavior is to render empty string for undefined vars

def test_render_with_custom_undefined_behavior(template_engine):
    """Test rendering with custom undefined variable behavior."""
    template_content = "{{ undefined_var | default('DEFAULT') }}"
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            result = template_engine.render("test.j2", {})
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_with_custom_undefined_behavior"})
            
            assert result == "DEFAULT"

def test_render_with_nested_context(template_engine):
    """Test rendering with nested context objects."""
    template_content = """{{ user.name }} ({{ user.role }})
{% for perm in user.permissions %}
- {{ perm }}
{% endfor %}"""
    
    context = {
        "user": {
            "name": "John",
            "role": "admin",
            "permissions": ["read", "write", "delete"]
        }
    }
    
    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('os.path.exists', return_value=True):
            result = template_engine.render("test.j2", context)
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_render_with_nested_context"})
            
            assert "John (admin)" in result
            assert "- read" in result
            assert "- write" in result
            assert "- delete" in result

def test_template_cache(template_engine):
    """Test template caching behavior."""
    template_content = "Hello {{ name }}!"
    mock_file = mock_open(read_data=template_content)
    
    with patch('builtins.open', mock_file):
        with patch('os.path.exists', return_value=True):
            # First render should read from file
            template_engine.render("test.j2", {"name": "World"})
            
            # Second render should use cached template
            template_engine.render("test.j2", {"name": "Cache"})
            log_event("TEST_ADDED", "TestTemplateEngine", {"test": "test_template_cache"})
            
            # File should only be opened once
            assert mock_file.call_count == 1 