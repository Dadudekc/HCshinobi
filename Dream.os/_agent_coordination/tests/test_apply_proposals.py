# tests/test_apply_proposals.py

import pytest
import os
import sys
from pathlib import Path
import subprocess # For running script as command line tool
import re
import unittest
from unittest.mock import patch, mock_open, MagicMock
from apply_proposals import apply_proposal_to_rulebook, update_proposal_status

# Add project root to allow importing apply_proposals
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Assuming apply_proposals exists at the root of _agent_coordination
# If moved later, update this import
import apply_proposals

# --- Fixtures ---

@pytest.fixture
def temp_dirs(tmp_path):
    """Creates temporary Agent1, proposals, and rulebook files."""
    agent1_dir = tmp_path / "Agent1"
    agent1_dir.mkdir()
    proposals_file = agent1_dir / "rulebook_update_proposals.md"
    rulebook_file = agent1_dir / "rulebook.md"
    
    # Patch global paths used by the module
    apply_proposals.PROPOSALS_FILE_PATH = proposals_file
    apply_proposals.RULEBOOK_PATH = rulebook_file
    
    return proposals_file, rulebook_file

@pytest.fixture
def sample_rulebook_content():
    return """# Rulebook

### Rule Locked
- **ID:** R-LOCKED
- Desc: This rule is locked.
```yaml
rules:
  - id: R-LOCKED
    locked: true 
```

### Rule Unlocked
- **ID:** R-UNLOCKED
- Desc: This rule is not locked.
```yaml
rules:
  - id: R-UNLOCKED
    locked: false
```

### Rule Missing Lock Field
- **ID:** R-NOLOCK
- Desc: This rule has no lock field.
```yaml
rules:
  - id: R-NOLOCK
    # no locked field
```
"""

@pytest.fixture
def sample_proposals_content():
    # Note: Using simple block IDs for now
    proposal_separator = "\n---\n"
    
    # Proposal targeting unlocked rule
    prop_unlocked = f"""### Proposal: Modify Unlocked
**Status:** Accepted
**Target Rule ID:** R-UNLOCKED

**Proposed Change Summary:**
Update R-UNLOCKED details.
"""

    # Proposal targeting locked rule
    prop_locked = f"""### Proposal: Modify Locked
**Status:** Accepted
**Target Rule ID:** R-LOCKED

**Proposed Change Summary:**
Update R-LOCKED details.
"""

    # Proposal targeting rule with no lock field
    prop_nolock = f"""### Proposal: Modify No Lock Field Rule
**Status:** Accepted
**Target Rule ID:** R-NOLOCK

**Proposed Change Summary:**
Update R-NOLOCK details.
"""

    # Proposal targeting non-existent rule
    prop_nonexistent = f"""### Proposal: Modify Non Existent
**Status:** Accepted
**Target Rule ID:** R-MISSING

**Proposed Change Summary:**
Create R-MISSING.
"""
    
    # Proposal that is NOT accepted
    prop_not_accepted = f"""### Proposal: Not Yet Accepted
**Status:** Proposed
**Target Rule ID:** R-UNLOCKED

**Proposed Change Summary:**
Update R-UNLOCKED eventually.
"""

    return proposal_separator.join([
        prop_unlocked, prop_locked, prop_nolock, prop_nonexistent, prop_not_accepted
    ])

# --- Helper to run script ---
def run_apply_proposals(args_list=None):
    """Runs apply_proposals.py as a subprocess."""
    script_path = Path(apply_proposals.__file__)
    command = [sys.executable, str(script_path)]
    if args_list:
        command.extend(args_list)
    
    result = subprocess.run(command, capture_output=True, text=True, cwd=script_path.parent)
    print("--- apply_proposals stdout ---")
    print(result.stdout)
    print("--- apply_proposals stderr ---")
    print(result.stderr)
    print("----------------------------")
    return result

# --- Tests for Rule Conflict Check --- #

def test_apply_proposal_unlocked_rule(temp_dirs, sample_rulebook_content, sample_proposals_content):
    """Test applying a proposal targeting an unlocked rule."""
    proposals_file, rulebook_file = temp_dirs
    rulebook_file.write_text(sample_rulebook_content, encoding='utf-8')
    proposals_file.write_text(sample_proposals_content, encoding='utf-8')

    result = run_apply_proposals()
    assert result.returncode == 0 # Should succeed
    
    updated_proposals_text = proposals_file.read_text(encoding='utf-8')
    # Check proposal R-UNLOCKED status is Applied
    assert "**Status:** Applied - Applied successfully." in updated_proposals_text
    assert "**Target Rule ID:** R-UNLOCKED" in updated_proposals_text
    
    # Check proposal R-LOCKED status is Blocked
    assert "**Status:** Blocked by Rule Conflict - Target rule R-LOCKED is locked." in updated_proposals_text
    assert "**Target Rule ID:** R-LOCKED" in updated_proposals_text
    
    # Check proposal R-NOLOCK status is Applied (assumes no lock field means not locked)
    assert "**Status:** Applied - Applied successfully." in updated_proposals_text
    assert "**Target Rule ID:** R-NOLOCK" in updated_proposals_text
    
    # Check rulebook content (basic append check for now)
    updated_rulebook_text = rulebook_file.read_text(encoding='utf-8')
    assert "[APPLIED" in updated_rulebook_text
    assert "Rule: R-UNLOCKED" in updated_rulebook_text
    assert "Rule: R-NOLOCK" in updated_rulebook_text
    assert "Rule: R-MISSING" in updated_rulebook_text # Non-existent target also applied
    assert "Rule: R-LOCKED" not in updated_rulebook_text # Locked rule change should not be appended

def test_apply_proposal_locked_rule_blocked(temp_dirs, sample_rulebook_content, sample_proposals_content):
    """Test that a proposal targeting a locked rule is blocked by default."""
    proposals_file, rulebook_file = temp_dirs
    rulebook_file.write_text(sample_rulebook_content, encoding='utf-8')
    proposals_file.write_text(sample_proposals_content, encoding='utf-8')

    result = run_apply_proposals()
    assert result.returncode == 0 # Script finishes, but proposal is blocked
    
    updated_proposals_text = proposals_file.read_text(encoding='utf-8')
    assert "**Status:** Blocked by Rule Conflict - Target rule R-LOCKED is locked." in updated_proposals_text
    assert "**Target Rule ID:** R-LOCKED" in updated_proposals_text

    # Check rulebook content - ensure original locked rule content wasn't changed / nothing appended for it
    original_rulebook_text = sample_rulebook_content
    updated_rulebook_text = rulebook_file.read_text(encoding='utf-8')
    assert "Rule: R-LOCKED" not in updated_rulebook_text.replace(original_rulebook_text, "") # Check nothing added for R-LOCKED

def test_apply_proposal_locked_rule_override(temp_dirs, sample_rulebook_content, sample_proposals_content):
    """Test that --override-rule-lock allows applying to a locked rule."""
    proposals_file, rulebook_file = temp_dirs
    rulebook_file.write_text(sample_rulebook_content, encoding='utf-8')
    proposals_file.write_text(sample_proposals_content, encoding='utf-8')

    result = run_apply_proposals(["--override-rule-lock"])
    assert result.returncode == 0 # Should succeed
    
    updated_proposals_text = proposals_file.read_text(encoding='utf-8')
    # Check proposal R-LOCKED status is Applied (due to override)
    assert "**Status:** Applied - Applied successfully." in updated_proposals_text
    assert "**Target Rule ID:** R-LOCKED" in updated_proposals_text

    # Check rulebook content - ensure R-LOCKED proposal was appended
    updated_rulebook_text = rulebook_file.read_text(encoding='utf-8')
    assert "[APPLIED" in updated_rulebook_text
    assert "Rule: R-LOCKED" in updated_rulebook_text

def test_apply_proposal_only_accepted_status(temp_dirs, sample_rulebook_content, sample_proposals_content):
    """Test that only proposals with status 'Accepted' are processed."""
    proposals_file, rulebook_file = temp_dirs
    rulebook_file.write_text(sample_rulebook_content, encoding='utf-8')
    proposals_file.write_text(sample_proposals_content, encoding='utf-8')
    
    result = run_apply_proposals()
    assert result.returncode == 0
    
    updated_proposals_text = proposals_file.read_text(encoding='utf-8')
    # Find the block for the 'Proposed' status proposal
    proposed_block_match = re.search(r"(### Proposal: Not Yet Accepted.*?)(?:\n---\n|\Z)", updated_proposals_text, re.DOTALL)
    assert proposed_block_match
    proposed_block_text = proposed_block_match.group(1)
    # Ensure its status hasn't changed to Applied or Blocked
    assert "**Status:** Proposed" in proposed_block_text
    assert "**Status:** Applied" not in proposed_block_text
    assert "**Status:** Blocked" not in proposed_block_text

# TODO: Add tests for:
# - Error handling during application (e.g., invalid proposal format causing apply_proposal_to_rulebook to fail)
# - Error handling during status update file writing
# - More sophisticated rule parsing and locking logic (when implemented)
# - Actual diff/patch application testing (when implemented)

class TestApplyProposals(unittest.TestCase):
    def setUp(self):
        # Mock the rulebook path
        self.mock_rulebook_path = MagicMock(spec=Path)
        self.mock_rulebook_path.read_text.return_value = """### Rule: RULE_001\nOriginal content\n### Rule: RULE_002\nAnother rule content"""

    @patch('apply_proposals.Path.write_text')
    def test_apply_proposal_to_existing_rule(self, mock_write_text):
        proposal = {
            'target_rule_id': 'RULE_001',
            'raw_content': "**Proposed Change Summary:**\nUpdated content for RULE_001"
        }
        apply_proposal_to_rulebook(proposal, self.mock_rulebook_path)
        # Don't check the exact timestamp since it's dynamic
        written_content = self.mock_rulebook_path.write_text.call_args[0][0]
        self.assertIn('Rule: RULE_001', written_content)
        self.assertIn('Updated content for RULE_001', written_content)
        self.assertIn('### Rule: RULE_002\nAnother rule content', written_content)

    @patch('apply_proposals.Path.write_text')
    def test_append_new_rule(self, mock_write_text):
        proposal = {
            'target_rule_id': 'RULE_003',
            'raw_content': "**Proposed Change Summary:**\nContent for new rule RULE_003"
        }
        apply_proposal_to_rulebook(proposal, self.mock_rulebook_path)
        self.assertIn('RULE_003', self.mock_rulebook_path.write_text.call_args[0][0])

    @patch('apply_proposals.Path')
    def test_update_proposal_status(self, mock_path_class):
        # Setup mock path instance
        mock_path_instance = MagicMock()
        mock_path_class.return_value = mock_path_instance
        mock_path_instance.read_text.return_value = "### proposal_block_0\n**Status:** Accepted\n**Target Rule ID:** RULE_001"
        
        # Call the function
        result = update_proposal_status('proposal_block_0', 'Applied', 'Successfully applied')
        
        # Verify the result and that write_text was called
        self.assertTrue(result)
        self.assertTrue(mock_path_instance.write_text.called)
        written_content = mock_path_instance.write_text.call_args[0][0]
        self.assertIn('Applied', written_content)
        self.assertIn('Successfully applied', written_content)

if __name__ == '__main__':
    unittest.main() 