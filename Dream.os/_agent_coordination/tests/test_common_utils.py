import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from utils.common_utils import add_proposal
import sys

def log_event(event_type, agent_id, data):
    """Mock log_event function for test coverage reporting."""
    print(f"[{event_type}] Agent: {agent_id}, Data: {data}")

@pytest.fixture
def valid_proposal_args():
    """Fixture providing valid proposal arguments."""
    return {
        "category": "ENHANCEMENT",
        "title": "Test Proposal",
        "context": "Test Context",
        "current_behavior": "Current behavior description",
        "proposed_change": "Proposed change description",
        "impact": "Expected impact",
        "implementation_notes": "Implementation details",
        "priority": 2
    }

@pytest.fixture
def mock_config():
    """Fixture providing a mock config module."""
    with patch.dict('sys.modules', {'config': MagicMock()}) as mocked_sys:
        config = MagicMock()
        sys.modules['config'] = config
        yield config

def test_add_proposal_valid(tmp_path, valid_proposal_args, mock_config):
    """Test adding a valid proposal."""
    mock_proposals_file = tmp_path / "proposals" / "rulebook_update_proposals.md"
    mock_config.PROPOSALS_FILE_PATH = mock_proposals_file
    
    with patch('builtins.print') as mock_print:
        result = add_proposal(**valid_proposal_args)
        
        assert result is True
        assert mock_proposals_file.exists()
        content = mock_proposals_file.read_text()
        
        # Verify all components are in the file
        assert "# Proposal Bank" in content
        assert "[P2][ENHANCEMENT] Test Proposal" in content
        assert "Test Context" in content
        assert "Current behavior description" in content
        assert "Proposed change description" in content
        assert "Expected impact" in content
        assert "Implementation details" in content
        
        mock_print.assert_any_call("✅ Successfully added proposal: Test Proposal")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_add_proposal_valid"})

def test_add_proposal_invalid_category(valid_proposal_args):
    """Test adding a proposal with invalid category."""
    with patch('builtins.print') as mock_print:
        invalid_args = valid_proposal_args.copy()
        invalid_args["category"] = "INVALID"
        
        result = add_proposal(**invalid_args)
        
        assert result is False
        mock_print.assert_called_with("Invalid category: INVALID. Must be one of ['ENHANCEMENT', 'BUG', 'REFACTOR', 'OPTIMIZATION', 'SECURITY', 'DOCS']")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_add_proposal_invalid_category"})

def test_add_proposal_invalid_priority(valid_proposal_args):
    """Test adding a proposal with invalid priority."""
    with patch('builtins.print') as mock_print:
        invalid_args = valid_proposal_args.copy()
        invalid_args["priority"] = 5
        
        result = add_proposal(**invalid_args)
        
        assert result is False
        mock_print.assert_called_with("Invalid priority: 5. Must be between 1 and 4")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_add_proposal_invalid_priority"})

def test_add_proposal_file_creation(tmp_path, valid_proposal_args, mock_config):
    """Test proposal file creation if it doesn't exist."""
    mock_proposals_file = tmp_path / "proposals" / "rulebook_update_proposals.md"
    mock_config.PROPOSALS_FILE_PATH = mock_proposals_file
    
    result = add_proposal(**valid_proposal_args)
    
    assert result is True
    assert mock_proposals_file.exists()
    assert mock_proposals_file.parent.exists()
    
    # First line should be the header
    content = mock_proposals_file.read_text().splitlines()
    assert content[0] == "# Proposal Bank"
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_add_proposal_file_creation"})

def test_add_proposal_file_append(tmp_path, valid_proposal_args, mock_config):
    """Test appending to existing proposal file."""
    mock_proposals_file = tmp_path / "proposals" / "rulebook_update_proposals.md"
    mock_proposals_file.parent.mkdir(parents=True)
    mock_proposals_file.write_text("# Proposal Bank\n\nExisting content\n---\n")
    mock_config.PROPOSALS_FILE_PATH = mock_proposals_file
    
    result = add_proposal(**valid_proposal_args)
    
    assert result is True
    content = mock_proposals_file.read_text()
    assert "Existing content" in content
    assert "[P2][ENHANCEMENT] Test Proposal" in content
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_add_proposal_file_append"})

def test_add_proposal_file_error(tmp_path, valid_proposal_args, mock_config):
    """Test handling of file write errors."""
    mock_proposals_file = tmp_path / "proposals" / "rulebook_update_proposals.md"
    mock_config.PROPOSALS_FILE_PATH = mock_proposals_file
    
    with patch('pathlib.Path.open', side_effect=PermissionError("Access denied")), \
         patch('builtins.print') as mock_print:
        result = add_proposal(**valid_proposal_args)
        
        assert result is False
        mock_print.assert_any_call("Error adding proposal: Access denied")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_add_proposal_file_error"})

def test_add_proposal_minimal(tmp_path, mock_config):
    """Test adding a proposal with minimal required arguments."""
    mock_proposals_file = tmp_path / "proposals" / "rulebook_update_proposals.md"
    mock_config.PROPOSALS_FILE_PATH = mock_proposals_file
    
    result = add_proposal(
        category="BUG",
        title="Minimal Proposal",
        context="Minimal context",
        current_behavior="Current",
        proposed_change="Change",
        impact="Impact"
    )
    
    assert result is True
    content = mock_proposals_file.read_text()
    assert "[P4][BUG] Minimal Proposal" in content  # Default priority
    assert "Implementation Notes:" not in content  # No implementation notes
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_add_proposal_minimal"})

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 