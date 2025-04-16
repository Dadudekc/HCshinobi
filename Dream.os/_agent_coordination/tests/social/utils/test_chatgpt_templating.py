"""Test suite for ChatGPT templating and dev log functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from social.utils.chatgpt_scraper import ChatGPTScraper, DevLogEntry, PromptTemplate

@pytest.fixture
def mock_session():
    """Create a mock session with required attributes."""
    session = Mock()
    session.get = Mock()
    session.post = Mock()
    session.headers = MagicMock()
    return session

@pytest.fixture
def scraper(mock_session):
    """Create a ChatGPTScraper instance with mocked session."""
    with patch('social.utils.chatgpt_scraper.requests.Session', return_value=mock_session):
        scraper = ChatGPTScraper()
        scraper.session = mock_session
        return scraper

@pytest.fixture
def sample_dev_log_entry():
    """Create a sample dev log entry."""
    return DevLogEntry(
        timestamp="2024-03-15 10:00:00",
        category="Combat System",
        title="Enhanced Spell Casting Mechanics",
        description="Implemented new spell casting system with channeling mechanics",
        changes=[
            "Added spell channeling time",
            "Implemented interruption mechanics",
            "Added visual feedback"
        ],
        impact={
            "gameplay": "More strategic combat decisions",
            "balance": "Increased risk-reward for spellcasters",
            "performance": "Minimal impact on server load"
        },
        version="1.2.0"
    )

class TestPromptTemplate:
    """Test suite for prompt template functionality."""

    def test_template_rendering(self):
        """Test basic template rendering."""
        template = PromptTemplate("Hello {{ name }}!")
        result = template.render(name="World")
        assert result == "Hello World!"

    def test_template_with_multiple_variables(self):
        """Test template with multiple variables."""
        template = PromptTemplate("{{ greeting }} {{ name }}! Version: {{ version }}")
        result = template.render(greeting="Hi", name="Tester", version="1.0")
        assert result == "Hi Tester! Version: 1.0"

class TestDevLogGeneration:
    """Test suite for dev log generation functionality."""

    @pytest.mark.asyncio
    async def test_create_dev_log_entry(self, scraper, mock_session):
        """Test creating a dev log entry."""
        mock_response = {
            "message": {
                "content": '''```json
                {
                    "timestamp": "2024-03-15 10:00:00",
                    "category": "Combat System",
                    "title": "Enhanced Spell Casting",
                    "description": "New spell casting system",
                    "changes": ["Added channeling"],
                    "impact": {
                        "gameplay": "More strategic",
                        "balance": "Better risk-reward",
                        "performance": "Minimal impact"
                    },
                    "version": "1.2.0"
                }
                ```'''
            }
        }
        mock_session.post.return_value.json.return_value = mock_response
        mock_session.post.return_value.status_code = 200

        entry = await scraper.create_dev_log_entry(
            feature_name="Spell Casting",
            category="Combat System",
            version="1.2.0"
        )

        assert isinstance(entry, DevLogEntry)
        assert entry.category == "Combat System"
        assert entry.version == "1.2.0"
        assert len(entry.changes) == 1

    def test_register_custom_template(self, scraper):
        """Test registering a custom template."""
        custom_template = '''
        Create patch notes for {{ feature }}:
        Version: {{ version }}
        '''
        scraper.register_template("patch_notes", custom_template)
        
        template = scraper.get_template("patch_notes")
        assert template is not None
        
        rendered = template.render(feature="New Feature", version="1.0")
        assert "New Feature" in rendered
        assert "Version: 1.0" in rendered

    def test_parse_dev_log_response(self, scraper):
        """Test parsing dev log response."""
        response = '''```json
        {
            "timestamp": "2024-03-15 10:00:00",
            "category": "Combat System",
            "title": "Enhanced Spell Casting",
            "description": "New spell casting system",
            "changes": ["Added channeling"],
            "impact": {
                "gameplay": "More strategic",
                "balance": "Better risk-reward",
                "performance": "Minimal impact"
            },
            "version": "1.2.0"
        }
        ```'''

        entry = scraper.parse_dev_log_response(response)
        assert isinstance(entry, DevLogEntry)
        assert entry.title == "Enhanced Spell Casting"
        assert len(entry.changes) == 1
        assert entry.impact["gameplay"] == "More strategic"

    def test_export_dev_log_markdown(self, scraper, sample_dev_log_entry):
        """Test exporting dev log entries to markdown."""
        markdown = scraper.export_dev_log([sample_dev_log_entry], format='markdown')
        
        assert "# MMORPG Development Log" in markdown
        assert "## Enhanced Spell Casting Mechanics" in markdown
        assert "**Category:** Combat System" in markdown
        assert "- Added spell channeling time" in markdown
        assert "**Gameplay:** More strategic combat decisions" in markdown

    def test_export_dev_log_json(self, scraper, sample_dev_log_entry):
        """Test exporting dev log entries to JSON."""
        json_output = scraper.export_dev_log([sample_dev_log_entry], format='json')
        
        assert "Enhanced Spell Casting Mechanics" in json_output
        assert "Combat System" in json_output
        assert "More strategic combat decisions" in json_output

    def test_invalid_export_format(self, scraper, sample_dev_log_entry):
        """Test handling of invalid export format."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            scraper.export_dev_log([sample_dev_log_entry], format='invalid') 