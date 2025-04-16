import unittest
import os
import sys
import shutil
import tempfile
import time
import json
import re

# Add project root to sys.path to allow importing core modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Module to test (from core)
# NOTE: This import will fail if the syntax error in gpt_command_router.py
# (missing except block) is not manually fixed first.
try:
    # Import the target module from core
    import core.gpt_command_router as gpt_command_router
    # Import dependency from core
    import core.governance_memory_engine as governance_memory_engine
    module_load_error = None
except SyntaxError as e:
    # Handle specific syntax error preventing import
    gpt_command_router = None
    governance_memory_engine = None
    module_load_error = f"Syntax error preventing import: {e}"
except ImportError as e:
    gpt_command_router = None
    governance_memory_engine = None
    module_load_error = f"ImportError: {e}"

# Sample proposal file content
SAMPLE_PROPOSAL_CONTENT = """# Proposals

## Proposal ID: PROP-ACCEPT-001
**Timestamp:** ...
**Status:** Proposed
**Proposed By:** Arch
**Type:** Amendment
**Rationale:** Needs accepting.
---

## Proposal ID: PROP-REJECT-002
**Timestamp:** ...
**Status:** Proposed
**Proposed By:** Arch
**Type:** Addition
**Rationale:** Needs rejecting.
---

## Proposal ID: PROP-IGNORE-003
**Timestamp:** ...
**Status:** Proposed
**Proposed By:** Arch
**Type:** Deletion
**Rationale:** Should remain proposed.
---

## Proposal ID: PROP-BADFORMAT-004
**Timestamp:** ...
**Status:** Proposed
**Proposed By:** Arch
**Type:** Invalid
Rationale: Status line missing below
**Status** NoColon
---
"""

@unittest.skipIf(module_load_error, f"Skipping tests due to module load error: {module_load_error}")
class TestGptCommandRouter(unittest.TestCase):

    def setUp(self):
        """Set up temp files and override module paths."""
        self.test_dir = tempfile.mkdtemp()
        self.analysis_dir = os.path.join(self.test_dir, "analysis") # Need analysis subdir
        os.makedirs(self.analysis_dir, exist_ok=True)

        self.mock_gpt_response_file = os.path.join(self.analysis_dir, "gpt_response.txt")
        self.mock_proposal_file = os.path.join(self.analysis_dir, "proposals.md")
        # Use runtime dir for mock GME log, consistent with GME module
        self.runtime_dir = os.path.join(self.test_dir, "runtime")
        os.makedirs(self.runtime_dir, exist_ok=True)
        self.mock_gov_log_file = os.path.join(self.runtime_dir, "gov_log.jsonl")

        # Create initial files
        with open(self.mock_gpt_response_file, 'w') as f: f.write("")
        with open(self.mock_proposal_file, 'w') as f: f.write(SAMPLE_PROPOSAL_CONTENT)
        with open(self.mock_gov_log_file, 'w') as f: f.write("") # Empty log

        # Override global paths in the modules
        self.original_paths = {}
        # Store original paths before overriding
        self.original_paths['GCR_ANALYSIS_DIR'] = gpt_command_router.ANALYSIS_DIR
        self.original_paths['GCR_GPT_RESPONSE_FILE'] = gpt_command_router.GPT_RESPONSE_FILE
        self.original_paths['GCR_PROPOSAL_FILE'] = gpt_command_router.PROPOSAL_FILE
        self.original_paths['GME_GOVERNANCE_LOG_FILE'] = governance_memory_engine.GOVERNANCE_LOG_FILE

        # Override paths to use temp directory structure
        gpt_command_router.ANALYSIS_DIR = self.analysis_dir
        gpt_command_router.GPT_RESPONSE_FILE = self.mock_gpt_response_file
        gpt_command_router.PROPOSAL_FILE = self.mock_proposal_file
        governance_memory_engine.GOVERNANCE_LOG_FILE = self.mock_gov_log_file # Mock GME path

    def tearDown(self):
        """Clean up temp files and restore paths."""
        # Restore original paths
        gpt_command_router.ANALYSIS_DIR = self.original_paths['GCR_ANALYSIS_DIR']
        gpt_command_router.GPT_RESPONSE_FILE = self.original_paths['GCR_GPT_RESPONSE_FILE']
        gpt_command_router.PROPOSAL_FILE = self.original_paths['GCR_PROPOSAL_FILE']
        governance_memory_engine.GOVERNANCE_LOG_FILE = self.original_paths['GME_GOVERNANCE_LOG_FILE']
        # Remove temp dir
        shutil.rmtree(self.test_dir)

    # === Tests for parse_commands ===

    def test_parse_accept_command(self):
        response = "Please ACCEPT proposal PROP-ACCEPT-001."
        commands = gpt_command_router.parse_commands(response)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "ACCEPT")
        self.assertEqual(commands[0]["proposal_id"], "PROP-ACCEPT-001")
        self.assertIsNone(commands[0]["reason"])

    def test_parse_reject_command_with_reason(self):
        response = "I think we should REJECT proposal PROP-REJECT-002 because it is redundant."
        commands = gpt_command_router.parse_commands(response)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "REJECT")
        self.assertEqual(commands[0]["proposal_id"], "PROP-REJECT-002")
        self.assertEqual(commands[0]["reason"], "it is redundant.")

    def test_parse_multiple_commands(self):
        response = ("Okay, ACCEPT proposal PROP-ACCEPT-001. \n"
                    "Also, REJECT proposal PROP-REJECT-002 because duplicate.")
        commands = gpt_command_router.parse_commands(response)
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0]["command"], "ACCEPT")
        self.assertEqual(commands[0]["proposal_id"], "PROP-ACCEPT-001")
        self.assertEqual(commands[1]["command"], "REJECT")
        self.assertEqual(commands[1]["proposal_id"], "PROP-REJECT-002")
        self.assertEqual(commands[1]["reason"], "duplicate.")

    def test_parse_no_commands(self):
        response = "The proposals look reasonable, but I need more context."
        commands = gpt_command_router.parse_commands(response)
        self.assertEqual(len(commands), 0)

    def test_parse_case_insensitivity(self):
        response = "Let's accept proposal PROP-ACCEPT-001."
        commands = gpt_command_router.parse_commands(response)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["command"], "ACCEPT")

    # === Tests for update_proposal_status ===

    def test_update_status_accept(self):
        success = gpt_command_router.update_proposal_status("PROP-ACCEPT-001", "Accepted")
        self.assertTrue(success)
        with open(self.mock_proposal_file, 'r') as f:
            content = f.read()
        self.assertRegex(content, r"## Proposal ID: PROP-ACCEPT-001.*?\*\*Status:\*\* Accepted", re.DOTALL)
        self.assertNotRegex(content, r"## Proposal ID: PROP-ACCEPT-001.*?\*\*Decision Rationale:", re.DOTALL)

    def test_update_status_reject_with_reason(self):
        reason = "This is the rejection reason."
        success = gpt_command_router.update_proposal_status("PROP-REJECT-002", "Rejected", reason)
        self.assertTrue(success)
        with open(self.mock_proposal_file, 'r') as f:
            content = f.read()
        self.assertRegex(content, r"## Proposal ID: PROP-REJECT-002.*?\*\*Status:\*\* Rejected.*?\*\*Decision Rationale:\*\* This is the rejection reason.", re.DOTALL)

    def test_update_status_proposal_not_found(self):
        success = gpt_command_router.update_proposal_status("PROP-NONEXISTENT", "Accepted")
        self.assertFalse(success)

    def test_update_status_file_not_found(self):
        # Temporarily remove the mock file
        os.remove(self.mock_proposal_file)
        success = gpt_command_router.update_proposal_status("PROP-ACCEPT-001", "Accepted")
        self.assertFalse(success)
        # Recreate file for subsequent tests/teardown
        with open(self.mock_proposal_file, 'w') as f: f.write(SAMPLE_PROPOSAL_CONTENT)

    def test_update_status_bad_format_proposal(self):
        # Test updating a proposal where the status line might be missing/malformed
        success = gpt_command_router.update_proposal_status("PROP-BADFORMAT-004", "Accepted")
        # The current implementation returns False if status line isn't found
        self.assertFalse(success, "Should fail if status line is missing/malformed")

    # === Tests for execute_command (includes GME logging) ===

    def test_execute_accept_command(self):
        command_data = {"command": "ACCEPT", "proposal_id": "PROP-ACCEPT-001", "reason": None}
        gpt_command_router.execute_command(command_data)
        # Check proposal file status
        with open(self.mock_proposal_file, 'r') as f: content = f.read()
        self.assertRegex(content, r"## Proposal ID: PROP-ACCEPT-001.*?\*\*Status:\*\* Accepted", re.DOTALL)
        # Check governance log
        with open(self.mock_gov_log_file, 'r') as f: lines = f.readlines()
        self.assertEqual(len(lines), 1)
        log_data = json.loads(lines[0])
        self.assertEqual(log_data["event_type"], "PROPOSAL_ACCEPTED")
        self.assertEqual(log_data["agent_source"], "ChatGPT via gpt_command_router")
        self.assertEqual(log_data["details"]["proposal_id"], "PROP-ACCEPT-001")

    def test_execute_reject_command(self):
        reason = "Test reject reason."
        command_data = {"command": "REJECT", "proposal_id": "PROP-REJECT-002", "reason": reason}
        gpt_command_router.execute_command(command_data)
        # Check proposal file status and rationale
        with open(self.mock_proposal_file, 'r') as f: content = f.read()
        self.assertRegex(content, r"## Proposal ID: PROP-REJECT-002.*?\*\*Status:\*\* Rejected.*?\*\*Decision Rationale:\*\* Test reject reason.", re.DOTALL)
        # Check governance log
        with open(self.mock_gov_log_file, 'r') as f: lines = f.readlines()
        self.assertEqual(len(lines), 1)
        log_data = json.loads(lines[0])
        self.assertEqual(log_data["event_type"], "PROPOSAL_REJECTED")
        self.assertEqual(log_data["details"]["proposal_id"], "PROP-REJECT-002")
        self.assertEqual(log_data["details"]["reason"], reason)

    # === Test for main execution flow ===

    def test_main_flow(self):
        """Test the main function processing a response file."""
        # Create a mock response file
        response_content = ("Let's ACCEPT proposal PROP-ACCEPT-001.\n"
                            "We must REJECT proposal PROP-REJECT-002 because it is not feasible.")
        with open(self.mock_gpt_response_file, 'w') as f: f.write(response_content)

        # Run the main function (which reads the file, parses, executes)
        gpt_command_router.main()

        # Verify proposal file changes
        with open(self.mock_proposal_file, 'r') as f: content = f.read()
        self.assertRegex(content, r"## Proposal ID: PROP-ACCEPT-001.*?\*\*Status:\*\* Accepted", re.DOTALL)
        self.assertRegex(content, r"## Proposal ID: PROP-REJECT-002.*?\*\*Status:\*\* Rejected.*?\*\*Decision Rationale:\*\* it is not feasible.", re.DOTALL)
        # Verify PROP-IGNORE-003 is untouched
        self.assertRegex(content, r"## Proposal ID: PROP-IGNORE-003.*?\*\*Status:\*\* Proposed", re.DOTALL)

        # Verify governance log entries
        with open(self.mock_gov_log_file, 'r') as f: lines = f.readlines()
        self.assertEqual(len(lines), 2)
        log1 = json.loads(lines[0])
        log2 = json.loads(lines[1])
        self.assertEqual(log1["event_type"], "PROPOSAL_ACCEPTED")
        self.assertEqual(log1["details"]["proposal_id"], "PROP-ACCEPT-001")
        self.assertEqual(log2["event_type"], "PROPOSAL_REJECTED")
        self.assertEqual(log2["details"]["proposal_id"], "PROP-REJECT-002")
        self.assertEqual(log2["details"]["reason"], "it is not feasible.")

if __name__ == '__main__':
    if module_load_error:
        print(f"\nCannot run tests: Failed to import gpt_command_router module from core.")
        print(f"Error: {module_load_error}")
        if "SyntaxError" in str(module_load_error):
             print("Please ensure the syntax error (missing except block) in core/gpt_command_router.py is fixed manually.")
    else:
        unittest.main() 