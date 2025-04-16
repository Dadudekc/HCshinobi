import os
import pytest
import yaml

# Add project root to path to allow importing the script
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions/constants from the script under test
from apply_proposals import (
    get_existing_rule_ids,
    parse_proposal,
    update_proposal_block_status,
    append_rule_to_rulebook,
    STATUS_ACCEPTED, STATUS_REJECTED, STATUS_PROPOSED, STATUS_PREFIX,
    PROPOSAL_SEPARATOR, APPLIED_RULES_HEADER
)

# --- Fixtures --- #

@pytest.fixture
def temp_rulebook(tmp_path):
    rulebook_content = """
# Existing Rules

### Rule 1
- ID: GEN-001
```yaml
rules:
  - id: GEN-001
    description: Rule one
```

### Rule 2
- ID: GEN-002
```yaml
rules:
  - id: GEN-002
    description: Rule two
```
"""
    file_path = tmp_path / "rulebook.md"
    file_path.write_text(rulebook_content, encoding='utf-8')
    return file_path

@pytest.fixture
def temp_proposals_file(tmp_path):
    proposals_content = f"""
### [REFLECT] Proposal 1
- **ID:** NEW-001
- **Origin:** reflection-abc
- **Reasoning:** Needs a new rule for X.
- **Proposed Description:** ...

```yaml
rules:
  - id: NEW-001
    description: A new rule for X.
    keywords: [x, y]
    applies_to: all_agents
```
{PROPOSAL_SEPARATOR}
### [AUTO] Proposal 2 - Duplicate ID
- **ID:** GEN-001
- **Origin:** monitor-xyz
- **Reasoning:** Clarification needed.

```yaml
rules:
  - id: GEN-001
    description: Duplicate rule ID.
    keywords: [a, b]
    applies_to: all_agents
```
{PROPOSAL_SEPARATOR}
### [REFLECT] Proposal 3 - Already Accepted
{STATUS_PREFIX}{STATUS_ACCEPTED}
- **ID:** OLD-001

```yaml
rules:
  - id: OLD-001
    description: Already accepted rule.
```
{PROPOSAL_SEPARATOR}
### [REFLECT] Proposal 4 - Bad YAML
- **ID:** BAD-001

```yaml
rules:
  - id: BAD-001
    description: Bad YAML
  unclosed_quote: "oops
```
{PROPOSAL_SEPARATOR}
### [REFLECT] Proposal 5 - Invalid Structure
- **ID:** BAD-002

```yaml
# Missing 'rules' key
rule:
  - id: BAD-002
    description: Invalid structure.
```
{PROPOSAL_SEPARATOR}
### [REFLECT] Proposal 6 - Valid Second Rule
- **ID:** NEW-002
- **Origin:** reflection-def
- **Reasoning:** Needs another rule.

```yaml
rules:
  - id: NEW-002
    description: Second new rule.
    keywords: [z]
    applies_to: Agent3
```
"""
    file_path = tmp_path / "rulebook_update_proposals.md"
    file_path.write_text(proposals_content, encoding='utf-8')
    return file_path


# --- Tests for get_existing_rule_ids --- #

def test_get_existing_rule_ids_success(temp_rulebook):
    ids = get_existing_rule_ids(temp_rulebook)
    assert ids == {"GEN-001", "GEN-002"}

def test_get_existing_rule_ids_empty(tmp_path):
    empty_file = tmp_path / "empty_rulebook.md"
    empty_file.touch()
    ids = get_existing_rule_ids(empty_file)
    assert ids == set()

def test_get_existing_rule_ids_no_file(tmp_path):
    non_existent_file = tmp_path / "non_existent.md"
    ids = get_existing_rule_ids(non_existent_file)
    assert ids == set()

# --- Tests for parse_proposal --- #

PROPOSAL_VALID = """
### [REFLECT] Proposal 1
- **ID:** NEW-001
```yaml
rules:
  - id: NEW-001
    description: A new rule.
```
"""
PROPOSAL_ACCEPTED = f"""
### [REFLECT] Proposal 3
{STATUS_PREFIX}{STATUS_ACCEPTED}
- **ID:** OLD-001
```yaml
rules:
  - id: OLD-001
```
"""
PROPOSAL_REJECTED = f"""
### [REFLECT] Proposal X
{STATUS_PREFIX}{STATUS_REJECTED} - Some Reason
- **ID:** REJ-001
```yaml
rules:
  - id: REJ-001
```
"""
PROPOSAL_BAD_YAML = """
### [REFLECT] Proposal 4
```yaml
rules:
  - id: BAD-001
    description: Bad YAML
  unclosed: "oops
```
"""
PROPOSAL_NO_YAML = """
### [REFLECT] Proposal 5
Just text, no yaml block.
"""
PROPOSAL_INVALID_STRUCTURE = """
### [REFLECT] Proposal 6
```yaml
not_rules:
  - id: BAD-002
```
"""
PROPOSAL_MISSING_ID = """
### [REFLECT] Proposal 7
```yaml
rules:
  - description: Missing ID
```
"""

def test_parse_proposal_valid():
    status, reason, rule_data = parse_proposal(PROPOSAL_VALID)
    assert status == STATUS_PROPOSED
    assert reason is None
    assert rule_data == {'id': 'NEW-001', 'description': 'A new rule.'}

def test_parse_proposal_already_accepted():
    status, reason, rule_data = parse_proposal(PROPOSAL_ACCEPTED)
    assert status == STATUS_ACCEPTED
    assert reason is None
    assert rule_data is None

def test_parse_proposal_already_rejected():
    status, reason, rule_data = parse_proposal(PROPOSAL_REJECTED)
    assert status == STATUS_REJECTED
    assert reason == "Some Reason"
    assert rule_data is None

def test_parse_proposal_bad_yaml():
    status, reason, rule_data = parse_proposal(PROPOSAL_BAD_YAML)
    assert status == STATUS_REJECTED
    assert "Invalid YAML syntax" in reason
    assert rule_data is None

def test_parse_proposal_no_yaml():
    status, reason, rule_data = parse_proposal(PROPOSAL_NO_YAML)
    assert status == STATUS_REJECTED
    assert reason == "No YAML block found in proposal."
    assert rule_data is None

def test_parse_proposal_invalid_structure():
    status, reason, rule_data = parse_proposal(PROPOSAL_INVALID_STRUCTURE)
    assert status == STATUS_REJECTED
    assert "does not contain a single rule" in reason
    assert rule_data is None

def test_parse_proposal_missing_id():
    status, reason, rule_data = parse_proposal(PROPOSAL_MISSING_ID)
    assert status == STATUS_REJECTED
    assert "missing id or description" in reason
    assert rule_data is None

# --- Tests for update_proposal_block_status --- #

def test_update_proposal_block_status_add_accepted():
    updated = update_proposal_block_status(PROPOSAL_VALID, STATUS_ACCEPTED)
    assert f"{STATUS_PREFIX}{STATUS_ACCEPTED}" in updated
    assert updated.count(f"{STATUS_PREFIX}") == 1

def test_update_proposal_block_status_add_rejected():
    updated = update_proposal_block_status(PROPOSAL_VALID, STATUS_REJECTED, "Test Reason")
    assert f"{STATUS_PREFIX}{STATUS_REJECTED} - Test Reason" in updated
    assert updated.count(f"{STATUS_PREFIX}") == 1

def test_update_proposal_block_status_replace_status():
    updated = update_proposal_block_status(PROPOSAL_REJECTED, STATUS_ACCEPTED)
    assert f"{STATUS_PREFIX}{STATUS_ACCEPTED}" in updated
    assert f"{STATUS_PREFIX}{STATUS_REJECTED}" not in updated
    assert updated.count(f"{STATUS_PREFIX}") == 1

# --- Tests for append_rule_to_rulebook --- #

@pytest.fixture
def empty_rulebook_path(tmp_path):
    return tmp_path / "new_rulebook.md"

def test_append_rule_creates_header(empty_rulebook_path):
    _, _, rule_data = parse_proposal(PROPOSAL_VALID)
    success = append_rule_to_rulebook(PROPOSAL_VALID, rule_data, empty_rulebook_path)
    assert success
    content = empty_rulebook_path.read_text(encoding='utf-8')
    assert APPLIED_RULES_HEADER in content
    assert "Rule ID: NEW-001" in content
    assert PROPOSAL_VALID in content

def test_append_rule_uses_existing_header(temp_rulebook):
    _, _, rule_data = parse_proposal(PROPOSAL_VALID)
    initial_content = temp_rulebook.read_text(encoding='utf-8')
    success = append_rule_to_rulebook(PROPOSAL_VALID, rule_data, temp_rulebook)
    assert success
    final_content = temp_rulebook.read_text(encoding='utf-8')
    # Header should only appear once
    assert final_content.count(APPLIED_RULES_HEADER.strip()) == 1 
    # Check if new rule block is appended
    assert PROPOSAL_VALID in final_content
    assert initial_content in final_content # Original content still exists

# --- Mocked Tests for Main Execution Logic (Example using mocker) --- #
# These would require mocking file reads/writes and potentially subprocess calls
# if the main script were more complex.

# Example structure:
def test_main_logic(mocker, tmp_path):
    # 1. Setup mock files using tmp_path
    mock_rulebook = tmp_path / "rulebook.md"
    mock_proposals = tmp_path / "proposals.md"
    mock_rulebook.write_text("# Rule GEN-001\n```yaml\nrules:\n  - id: GEN-001\n```")
    mock_proposals.write_text("### Proposal NEW-001\n```yaml\nrules:\n  - id: NEW-001\n    description: Test\n```")

    # 2. Patch file paths in the script under test
    mocker.patch('apply_proposals.RULEBOOK_PATH', mock_rulebook)
    mocker.patch('apply_proposals.PROPOSALS_FILE_PATH', mock_proposals)

    # 3. (Optional) Mock specific functions like get_existing_rule_ids if needed
    # mock_get_ids = mocker.patch('apply_proposals.get_existing_rule_ids', return_value={"GEN-001"})

    # 4. Run the main logic (requires refactoring main into a function)
    # apply_proposals.main_function() # Assuming main logic is in a function

    # 5. Assertions: Check content of mock_rulebook and mock_proposals
    # proposals_content = mock_proposals.read_text()
    # rulebook_content = mock_rulebook.read_text()
    # assert STATUS_ACCEPTED in proposals_content
    # assert "Rule ID: NEW-001" in rulebook_content
    pass # Placeholder - main logic needs refactoring for direct testing 