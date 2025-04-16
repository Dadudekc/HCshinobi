import os
import pytest
from unittest.mock import patch, MagicMock
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from template_engine import render_template, generate_post_from_template, env

def log_event(event_type, agent_id, data):
    """Mock log_event function for test coverage reporting."""
    print(f"[{event_type}] Agent: {agent_id}, Data: {data}")

@pytest.fixture
def mock_template_env(tmp_path):
    """Create a temporary template directory with test templates."""
    template_dir = tmp_path / "templates" / "social"
    template_dir.mkdir(parents=True)
    
    # Create test templates
    base_template = tmp_path / "templates" / "base.j2"
    base_template.write_text("Title: {{ title }}\nBody: {{ body }}", encoding='utf-8')
    
    twitter_template = template_dir / "twitter_post.j2"
    twitter_template.write_text("🚨 {{ title }}\n\n{{ proposal_summary }}\n\nStatus: {{ status_update }}", encoding='utf-8')
    
    return tmp_path / "templates"

@pytest.fixture
def setup_env(mock_template_env):
    """Setup the Jinja environment with our test templates."""
    with patch('template_engine.EXISTING_TEMPLATE_DIRS', [str(mock_template_env)]):
        with patch('template_engine.env', Environment(
            loader=FileSystemLoader(str(mock_template_env)),
            autoescape=select_autoescape([])
        )):
            yield

def test_render_valid_template(setup_env):
    """Test rendering a valid template with context."""
    context = {'title': 'Test Title', 'body': 'Test Body'}
    result = render_template('base.j2', context)
    assert 'Test Title' in result
    assert 'Test Body' in result
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_render_valid_template"})

def test_render_missing_template(setup_env):
    """Test handling of missing template."""
    with pytest.raises(TemplateNotFound):
        render_template('nonexistent.j2', {})

def test_render_invalid_context(setup_env):
    """Test handling of invalid context (missing variables)."""
    result = render_template('base.j2', {})
    assert 'Missing variables' in result
    assert 'Error rendering base.j2' in result

def test_generate_twitter_post(setup_env):
    """Test generating a Twitter post from template."""
    context = {
        "title": "Test Alert",
        "proposal_summary": "Test Proposal",
        "status_update": "Pending"
    }
    result = generate_post_from_template('twitter', context)
    assert '🚨 Test Alert' in result
    assert 'Test Proposal' in result
    assert 'Status: Pending' in result
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_generate_twitter_post"})

def test_generate_post_invalid_platform(setup_env):
    """Test handling of invalid social media platform."""
    context = {"title": "Test"}
    result = generate_post_from_template('invalid_platform', context)
    assert 'Error' in result
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_generate_post_invalid_platform"})

def test_env_initialization_no_template_dirs():
    """Test environment initialization with no valid template directories."""
    with patch('template_engine.EXISTING_TEMPLATE_DIRS', []):
        with patch('template_engine.env', None):
            result = render_template('any.j2', {})
            assert 'Error' in result
            assert 'Jinja environment missing' in result
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_env_initialization_no_template_dirs"})

def test_template_whitespace_handling(setup_env):
    """Test that template whitespace is handled correctly."""
    context = {
        "title": "  Padded Title  ",
        "proposal_summary": "\nProposal with extra newlines\n\n",
        "status_update": "Status"
    }
    result = generate_post_from_template('twitter', context)
    # Check that there are no empty lines between content
    lines = [line for line in result.splitlines() if line.strip()]
    assert len(lines) == len(result.splitlines())  # All lines should have content
    assert "Padded Title" in result  # Content should be preserved
    assert "Proposal with extra newlines" in result
    assert "Status" in result
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_template_whitespace_handling"})

def test_variable_detection_simple(setup_env):
    """Test detection of simple variables in templates."""
    with patch('template_engine.env') as mock_env:
        template_source = "Hello {{ name }}! Your age is {{ age }}."
        mock_template = MagicMock()
        mock_template.source = template_source
        mock_env.get_template.return_value = mock_template
        mock_env.parse.return_value = Environment().parse(template_source)
        
        # Should fail due to missing variables
        result = render_template('test.j2', {'name': 'John'})
        assert 'Missing variables' in result
        assert 'age' in result
        
        # Should succeed with all variables
        result = render_template('test.j2', {'name': 'John', 'age': 30})
        assert 'Missing variables' not in result
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_variable_detection_simple"})

def test_variable_detection_with_filters(setup_env):
    """Test detection of variables used with Jinja filters."""
    with patch('template_engine.env') as mock_env:
        template_source = "{{ name|upper }} has {{ coins|sum }} coins."
        mock_template = MagicMock()
        mock_template.source = template_source
        mock_env.get_template.return_value = mock_template
        mock_env.parse.return_value = Environment().parse(template_source)
        
        result = render_template('test.j2', {'name': 'John', 'coins': [1, 2, 3]})
        assert 'Missing variables' not in result
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_variable_detection_with_filters"})

def test_variable_detection_nested(setup_env):
    """Test detection of nested variable access."""
    with patch('template_engine.env') as mock_env:
        template_source = """
        {{ user.name }} works at {{ user.company.name }}.
        Department: {{ user.company.department }}
        """
        mock_template = MagicMock()
        mock_template.source = template_source
        mock_template.render.return_value = "John works at TechCorp.\nDepartment: R&D"
        mock_env.get_template.return_value = mock_template
        mock_env.parse.return_value = Environment().parse(template_source)
        mock_env.loader = MagicMock()
        mock_env.loader.get_source.return_value = (template_source, None, None)
        
        context = {
            'user': {
                'name': 'John',
                'company': {
                    'name': 'TechCorp',
                    'department': 'R&D'
                }
            }
        }
        result = render_template('test.j2', context)
        assert 'Missing variables' not in result
        assert 'John' in result
        assert 'TechCorp' in result
        assert 'R&D' in result
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_variable_detection_nested"})

def test_malformed_template(setup_env):
    """Test handling of malformed templates."""
    with patch('template_engine.env') as mock_env:
        template_source = "{{ unclosed variable"  # Malformed template
        mock_template = MagicMock()
        mock_template.source = template_source
        mock_env.get_template.return_value = mock_template
        mock_env.parse.side_effect = Exception("Template syntax error")
        
        with pytest.raises(Exception):
            render_template('malformed.j2', {})
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_malformed_template"})

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 