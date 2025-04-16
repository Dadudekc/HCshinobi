# _agent_coordination/apply_proposals.py

import logging
# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ApplyProposals")

import re
import argparse
from pathlib import Path
import yaml
from datetime import datetime

# Import paths and constants from config
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Import the new utility
from _agent_coordination.tools.rulebook_utils import load_rules

# Constants
STATUS_PREFIX = "**Status:**"
STATUS_ACCEPTED = "Accepted"
STATUS_APPLIED = "Applied"
STATUS_ERROR_APPLYING = "Error Applying"
STATUS_BLOCKED_BY_RULE = "Blocked by Rule Lock"

# --- Constants (Now use config) ---
PROPOSALS_FILE_PATH = config.PROPOSALS_FILE_PATH
RULEBOOK_PATH = config.RULEBOOK_PATH
PROPOSAL_SEPARATOR = config.PROPOSAL_SEPARATOR

# --- Functions --- #

def parse_proposals(proposals_path):
    """Parses proposals from the Markdown file."""
    proposals = []
    try:
        content = Path(proposals_path).read_text(encoding='utf-8')
        proposal_blocks = content.strip().split(PROPOSAL_SEPARATOR)
        for i, block in enumerate(proposal_blocks):
            block = block.strip()
            if not block: continue
            
            proposal = {
                "id": f"proposal_block_{i}", # Placeholder ID
                "raw_content": block,
                "status": None,
                "target_rule_id": None
            }
            
            status_match = re.search(rf"^{re.escape(STATUS_PREFIX)}(.*?)(?: - |$)", block, re.MULTILINE)
            if status_match: proposal["status"] = status_match.group(1).strip()
            
            rule_id_match = re.search(r"^\*\*Target Rule ID:\*\*\s*([\w\-]+)", block, re.MULTILINE)
            if rule_id_match: proposal["target_rule_id"] = rule_id_match.group(1)
            
            proposals.append(proposal)
    except FileNotFoundError:
        logger.warning(f"Proposals file not found: {proposals_path}. No proposals to apply.")
    except Exception as e:
        logger.error(f"Error parsing proposals file {proposals_path}: {e}")
    return proposals

def apply_proposal_to_rulebook(proposal, rulebook_path):
    """Applies a single proposal to the rulebook file."""
    logger.info(f"Attempting to apply proposal for rule: {proposal.get('target_rule_id', 'Unknown')}")
    target_rule_id = proposal.get('target_rule_id')
    timestamp = datetime.now().isoformat()
    applied_rule_header = f"### [APPLIED {timestamp}] Rule: {target_rule_id}"

    # Read the current rulebook content
    rulebook_content = rulebook_path.read_text(encoding='utf-8')

    # Locate the target rule
    rule_pattern = re.compile(rf"### Rule: {target_rule_id}\b.*?(?=### Rule:|\Z)", re.DOTALL)
    match = rule_pattern.search(rulebook_content)

    if match:
        # Existing rule found, apply changes
        logger.info(f"Found existing rule {target_rule_id}. Applying changes.")
        original_rule = match.group(0)
        proposed_change_match = re.search(r"\*\*Proposed Change Summary:\*\*\n(.*?)(?:\n\n\*\*Original Rule|\Z)", proposal['raw_content'], re.DOTALL | re.MULTILINE)
        proposed_content = proposed_change_match.group(1).strip() if proposed_change_match else "(Could not extract proposed content)"

        # Create a diff/patch (simplified for demonstration)
        new_rule = f"{applied_rule_header}\n{proposed_content}\n"
        rulebook_content = rulebook_content.replace(original_rule, new_rule)
    else:
        # New rule, append to rulebook
        logger.info(f"Rule {target_rule_id} not found. Appending as new rule.")
        proposed_change_match = re.search(r"\*\*Proposed Change Summary:\*\*\n(.*?)(?:\n\n\*\*Original Rule|\Z)", proposal['raw_content'], re.DOTALL | re.MULTILINE)
        proposed_content = proposed_change_match.group(1).strip() if proposed_change_match else "(Could not extract proposed content)"

        new_rule_text = f"\n---\n{applied_rule_header}\nBased on Proposal: {proposal.get('id')}\n{proposed_content}\n---\n"
        rulebook_content += new_rule_text

    # Write the updated rulebook content
    rulebook_path.write_text(rulebook_content, encoding='utf-8')
    logger.info(f"Applied proposal {proposal.get('id')} successfully.")
    return rulebook_content

def update_proposal_status(proposal_block, new_status, reason="", proposals_path=PROPOSALS_FILE_PATH):
    """Updates the status of a specific proposal block in the file."""
    # This requires reading the whole file, finding the block, updating, and rewriting.
    # It's inefficient but necessary without persistent proposal IDs.
    try:
        proposals_content = Path(proposals_path).read_text(encoding='utf-8')
        proposal_blocks = proposals_content.strip().split(PROPOSAL_SEPARATOR)
        updated_blocks = []
        found = False
        
        for i, block in enumerate(proposal_blocks):
            current_block_id = f"proposal_block_{i}" # Match placeholder ID
            if current_block_id == proposal_block:
                found = True
                lines = block.strip().split('\n')
                new_status_line = f"{STATUS_PREFIX}{new_status}"
                if reason: new_status_line += f" - {reason}"
                
                # Replace existing status line
                new_lines = [new_status_line if line.startswith(STATUS_PREFIX) else line for line in lines]
                # Add status line if it wasn't there (shouldn't happen for accepted)
                if not any(line.startswith(STATUS_PREFIX) for line in lines):
                    # Insert after header (assuming '###')
                     header_idx = next((j for j, l in enumerate(lines) if l.startswith("###")), -1)
                     if header_idx != -1:
                         new_lines.insert(header_idx + 1, new_status_line)
                     else:
                         new_lines.insert(0, new_status_line)
                         
                updated_blocks.append("\n".join(new_lines))
            else:
                updated_blocks.append(block)
                
        if found:
            new_content = PROPOSAL_SEPARATOR.join(updated_blocks).strip() + "\n"
            Path(proposals_path).write_text(new_content, encoding='utf-8')
            logger.info(f"Updated status for proposal {proposal_block} to {new_status}.")
            return True
        else:
            logger.warning(f"Could not find proposal {proposal_block} in {proposals_path} to update status.")
            return False
            
    except Exception as e:
        logger.error(f"Failed to update status for proposal {proposal_block} in {proposals_path}: {e}")
        return False

# --- Main Logic --- #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply accepted rulebook update proposals.")
    parser.add_argument("--override-rule-lock", action="store_true", 
                        help="Apply proposals even if the target rule is locked.")
    args = parser.parse_args()

    logger.info(f"Starting proposal application from {PROPOSALS_FILE_PATH} to {RULEBOOK_PATH}")
    logger.info(f"Override locked rules: {args.override_rule_lock}")

    try:
        # Use the utility function to load rules
        rule_lock_status = {rule_id: data["locked"] 
                           for rule_id, data in load_rules(RULEBOOK_PATH).items()}
        logger.info(f"Loaded lock status for {len(rule_lock_status)} rules.")
        proposals = parse_proposals(PROPOSALS_FILE_PATH)
    except FileNotFoundError as e:
        logger.error(f"Error loading files: {e}. Aborting.")
        exit(1)
    except Exception as e:
        logger.error(f"Error during initial loading: {e}. Aborting.")
        exit(1)

    applied_count = 0
    blocked_count = 0
    error_count = 0
    skipped_count = 0

    for proposal_block, proposal_data in proposals:
        if proposal_data.get("status", "").strip() != STATUS_ACCEPTED:
            logger.debug(f"Skipping proposal (ID: {proposal_data.get('id', 'N/A')}) with status: {proposal_data.get('status', 'N/A')}")
            skipped_count += 1
            continue

        target_rule_id = proposal_data.get("target_rule_id")
        if not target_rule_id:
            logger.error(f"Proposal missing 'Target Rule ID'. Cannot process: {proposal_data.get('id', 'Block Start')[:50]}...")
            update_proposal_status(proposal_block, STATUS_ERROR_APPLYING, "Missing Target Rule ID", PROPOSALS_FILE_PATH)
            error_count += 1
            continue

        # Check Rule Lock Conflict - Use the loaded lock status
        if target_rule_id in rule_lock_status and rule_lock_status[target_rule_id] and not args.override_rule_lock:
            logger.warning(f"Proposal for rule {target_rule_id} blocked: Rule is locked and override flag is OFF.")
            update_proposal_status(proposal_block, STATUS_BLOCKED_BY_RULE, f"Target rule {target_rule_id} is locked.", PROPOSALS_FILE_PATH)
            blocked_count += 1
            continue
        elif target_rule_id in rule_lock_status and rule_lock_status[target_rule_id] and args.override_rule_lock:
            logger.info(f"Overriding lock for proposal targeting rule {target_rule_id}.")
        elif target_rule_id not in rule_lock_status:
             logger.warning(f"Proposal targets rule {target_rule_id} which was not found in the rulebook during initial load. Allowing application cautiously.")

        # Apply the proposal (Placeholder logic)
        try:
            logger.info(f"Applying proposal targeting rule {target_rule_id}...")
            apply_proposal_to_rulebook(proposal_data, RULEBOOK_PATH)
            update_proposal_status(proposal_block, STATUS_APPLIED, "Applied successfully.", PROPOSALS_FILE_PATH)
            applied_count += 1
            logger.info(f"Successfully applied proposal for rule {target_rule_id}.")
        except Exception as e:
            logger.error(f"Failed to apply proposal for rule {target_rule_id}: {e}")
            update_proposal_status(proposal_block, STATUS_ERROR_APPLYING, str(e), PROPOSALS_FILE_PATH)
            error_count += 1

    logger.info("--- Proposal Application Summary ---")
    logger.info(f"Applied: {applied_count}")
    logger.info(f"Blocked (Rule Lock): {blocked_count}")
    logger.info(f"Errors: {error_count}")
    logger.info(f"Skipped (Status not Accepted): {skipped_count}")
    logger.info("----------------------------------")

    if error_count > 0:
        exit(1)
    else:
        exit(0) 