import unittest
import os
import sys
import json
import shutil
import tempfile
from datetime import datetime, timezone

# Add project root to sys.path to allow importing the module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Module to test
import governance_scraper

class TestGovernanceScraper(unittest.TestCase):

    def setUp(self):
        """Set up temporary directories and mock files for testing."""
        self.test_dir = tempfile.mkdtemp()
        self.analysis_dir = os.path.join(self.test_dir, "analysis")
        self.agent_coord_dir = os.path.join(self.test_dir, "_agent_coordination")
        self.agent1_dir = os.path.join(self.agent_coord_dir, "Agent1")
        self.agent2_dir = os.path.join(self.agent_coord_dir, "Agent2")
        self.agent1_reflection_dir = os.path.join(self.agent1_dir, "reflection")
        self.agent2_reflection_dir = os.path.join(self.agent2_dir, "reflection")

        # Create directories
        os.makedirs(self.analysis_dir, exist_ok=True)
        os.makedirs(self.agent1_dir, exist_ok=True)
        os.makedirs(self.agent2_dir, exist_ok=True)
        os.makedirs(self.agent1_reflection_dir, exist_ok=True)
        os.makedirs(self.agent2_reflection_dir, exist_ok=True)

        # --- Create Mock Files ---
        self.mock_gov_log = os.path.join(self.agent1_dir, "governance_memory.jsonl")
        self.mock_rulebook = os.path.join(self.agent1_dir, "rulebook.md")
        self.mock_proposals = os.path.join(self.analysis_dir, "rulebook_update_proposals.md")
        self.mock_reflect1 = os.path.join(self.agent1_reflection_dir, "reflection_log.md")
        self.mock_reflect2 = os.path.join(self.agent2_reflection_dir, "reflection_log.md")

        # Write content to mock files
        with open(self.mock_gov_log, 'w') as f:
            f.write(json.dumps({"event_id": "evt1", "timestamp": datetime.now(timezone.utc).isoformat(), "event_type": "T1", "agent_source": "A1", "details": {}}) + '\n')
            f.write(json.dumps({"event_id": "evt2", "timestamp": datetime.now(timezone.utc).isoformat(), "event_type": "T2", "agent_source": "A2", "details": {}}) + '\n')

        with open(self.mock_rulebook, 'w') as f:
            f.write("### Rule: R1\nDescription: D1\n### Rule: R2\nDescription: D2\n# --- AUTO-APPLIED RULE ---")

        with open(self.mock_proposals, 'w') as f:
            f.write("## Proposal ID: P1\n**Status:** Proposed\n**Type:** T1\n**Rationale:** R1\n---\n## Proposal ID: P2\n**Status:** Applied\n**Type:** T2\n**Rationale:** R2\n---\n## Proposal ID: P3\n**Status:** Proposed\n**Type:** T3\n**Rationale:** R3\n---")

        with open(self.mock_reflect1, 'w') as f:
            f.write("---\n**Reflection Timestamp:** 2024-01-01T12:00:00Z\n**Alert ID:** A1\n**Disposition:** D1\n**Justification:** J1\n---")
        with open(self.mock_reflect2, 'w') as f:
            f.write("---\n**Reflection Timestamp:** 2024-01-01T13:00:00Z\n**Alert ID:** A2\n**Disposition:** D2\n**Justification:** J2\n---")

        # --- Override scraper's global paths ---
        self.original_paths = {}
        self.original_paths['AGENT_COORD_DIR'] = governance_scraper.AGENT_COORD_DIR
        self.original_paths['GOVERNANCE_LOG_FILE'] = governance_scraper.GOVERNANCE_LOG_FILE
        self.original_paths['RULEBOOK_PATH'] = governance_scraper.RULEBOOK_PATH
        self.original_paths['PROPOSAL_FILE'] = governance_scraper.PROPOSAL_FILE
        self.original_paths['REFLECTION_LOG_PATTERN'] = governance_scraper.REFLECTION_LOG_PATTERN

        governance_scraper.AGENT_COORD_DIR = self.agent_coord_dir
        # Adjust paths to point within the temp test directory
        governance_scraper.GOVERNANCE_LOG_FILE = self.mock_gov_log
        governance_scraper.RULEBOOK_PATH = self.mock_rulebook
        governance_scraper.PROPOSAL_FILE = self.mock_proposals
        # Adjust pattern to match within the temp directory
        governance_scraper.REFLECTION_LOG_PATTERN = os.path.join(self.agent_coord_dir, "*", "reflection", "reflection_log.md")

        print(f"NOTE: Redirected scraper paths to use temp dir: {self.test_dir}")

    def tearDown(self):
        """Clean up temporary directory and restore original paths."""
        # Restore original paths
        for key, val in self.original_paths.items():
            setattr(governance_scraper, key, val)

        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_load_recent_governance_events(self):
        """Test loading governance events."""
        events = governance_scraper.load_recent_governance_events(max_lines=5)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_id"], "evt1")
        self.assertEqual(events[1]["event_id"], "evt2")

    def test_load_recent_reflections(self):
        """Test loading reflections from multiple agents."""
        reflections = governance_scraper.load_recent_reflections(max_reflections=5)
        self.assertEqual(len(reflections), 2)
        # Note: Order might vary based on glob, sort is best-effort string sort
        alert_ids = {r["alert_id"] for r in reflections}
        self.assertSetEqual(alert_ids, {"A1", "A2"})

    def test_load_proposals_proposed(self):
        """Test loading only 'Proposed' proposals."""
        proposals = governance_scraper.load_proposals(status_filter="Proposed")
        self.assertEqual(len(proposals), 2)
        self.assertEqual(proposals[0]["id"], "P1")
        self.assertEqual(proposals[1]["id"], "P3")

    def test_load_proposals_all(self):
        """Test loading all proposals when filter is None."""
        proposals = governance_scraper.load_proposals(status_filter=None)
        self.assertEqual(len(proposals), 3)

    def test_get_rulebook_summary(self):
        """Test the rulebook summary generation."""
        summary = governance_scraper.get_rulebook_summary()
        self.assertIn("2 core rules", summary) # 2 rules starting with ### Rule:
        self.assertIn("1 auto-applied rules", summary) # Count of auto-applied marker

    def test_generate_governance_data(self):
        """Test the main data generation function."""
        data = governance_scraper.generate_governance_data()
        self.assertIsInstance(data, dict)
        self.assertIn("rulebook_summary", data)
        self.assertIn("open_proposals", data)
        self.assertIn("recent_reflections", data)
        self.assertIn("recent_events", data)
        self.assertEqual(len(data["open_proposals"]), 2)
        self.assertEqual(len(data["recent_reflections"]), 2)
        self.assertEqual(len(data["recent_events"]), 2)
        self.assertEqual(data['recent_hours'], governance_scraper.RECENT_HOURS)
        self.assertEqual(data['max_log_lines'], governance_scraper.MAX_LOG_LINES)

if __name__ == '__main__':
    unittest.main() 