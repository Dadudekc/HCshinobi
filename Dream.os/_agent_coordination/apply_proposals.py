# _agent_coordination/apply_proposals.py

import os
import re
import yaml
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ProposalApplier")

# --- Configuration ---
# Assuming script run from _agent_coordination or paths adjusted
AGENT1_DIR = Path("Agent1")
PROPOSALS_FILE_PATH = AGENT1_DIR / "rulebook_update_proposals.md"
RULEBOOK_PATH = AGENT1_DIR / "rulebook.md"
PROPOSAL_SEPARATOR = "\n---\n"
STATUS_ACCEPTED = "Accepted" # Status required for application
STATUS_APPLIED = "Applied"
STATUS_ERROR_APPLYING = "Error Applying"
STATUS_BLOCKED_BY_RULE = "Blocked by Rule Conflict"
STATUS_PREFIX = "**Status:** "

# --- Rulebook Interaction ---
def load_rules_from_rulebook(filepath=RULEBOOK_PATH):
    """Loads rule definitions from the rulebook (simplified)."""
    # This is a basic version; consider reusing logic from reflection_agent if more robust parsing exists
    rules = {}
    try:
        content = filepath.read_text(encoding='utf-8')
        # Simple extraction based on ID line - needs improvement for complex rules/locking
        for match in re.finditer(r"^- \*\*ID:\*\*\s*([\w\-]+)", content, re.MULTILINE):
            rule_id = match.group(1)
            # TODO: Add logic to check if rule is marked as "locked" or "immutable"
            is_locked = False # Placeholder
            rules[rule_id] = {"id": rule_id, "locked": is_locked}
        logger.info(f"Loaded {len(rules)} rule IDs from {filepath}.")
    except FileNotFoundError:
        logger.error(f"Rulebook file not found: {filepath}")
    except Exception as e:
        logger.error(f"Error reading rulebook {filepath}: {e}")
    return rules

# --- Proposal Parsing (Simplified - Reuse from meta_architect if available) ---
def parse_proposals(filepath=PROPOSALS_FILE_PATH):
    """Loads proposals, focusing on accepted ones."""
    proposals = []
    try:
        content = Path(filepath).read_text(encoding='utf-8')
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
        logger.warning(f"Proposals file not found: {filepath}. No proposals to apply.")
    except Exception as e:
        logger.error(f"Error parsing proposals file {filepath}: {e}")
    return proposals

# --- Proposal Application Logic (Basic) ---
def apply_proposal_to_rulebook(proposal, rulebook_content):
    """Applies a single proposal to the rulebook content string.
       This is a placeholder - requires actual diff/patch logic or targeted rewrite.
    """
    logger.info(f"Attempting to apply proposal for rule: {proposal.get('target_rule_id', 'Unknown')}")
    # Placeholder: Simply append proposal content as a new rule section
    # TODO: Implement robust logic: find target rule, apply changes (diff/patch?), handle new rules.
    timestamp = datetime.now().isoformat()
    applied_rule_header = f"### [APPLIED {timestamp}] Rule: {proposal.get('target_rule_id', 'NEW_RULE')}"
    
    # Corrected Regex: Capture content until \n\n**Original Rule or end of string (\Z)
    proposed_change_match = re.search(r"\*\*Proposed Change Summary:\*\*\n(.*?)(?:\n\n\*\*Original Rule|\Z)", proposal['raw_content'], re.DOTALL | re.MULTILINE)
    proposed_content = proposed_change_match.group(1).strip() if proposed_change_match else "(Could not extract proposed content)"
    
    new_rule_text = f"\n---\n{applied_rule_header}\nBased on Proposal: {proposal.get('id')}\n{proposed_content}\n---\n"
    
    # For now, just append
    rulebook_content += new_rule_text
    logger.info(f"Applied proposal {proposal.get('id')} (placeholder append).")
    return rulebook_content

# --- Status Update Logic (Similar to meta_architect) ---
def update_proposal_status_in_file(proposal_id, new_status, reason, filepath=PROPOSALS_FILE_PATH):
    """Updates the status of a specific proposal within the proposals file."""
    # This requires reading the whole file, finding the block, updating, and rewriting.
    # It's inefficient but necessary without persistent proposal IDs.
    try:
        proposals_content = Path(filepath).read_text(encoding='utf-8')
        proposal_blocks = proposals_content.strip().split(PROPOSAL_SEPARATOR)
        updated_blocks = []
        found = False
        
        for i, block in enumerate(proposal_blocks):
            current_block_id = f"proposal_block_{i}" # Match placeholder ID
            if current_block_id == proposal_id:
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
            Path(filepath).write_text(new_content, encoding='utf-8')
            logger.info(f"Updated status for proposal {proposal_id} to {new_status}.")
            return True
        else:
            logger.warning(f"Could not find proposal {proposal_id} in {filepath} to update status.")
            return False
            
    except Exception as e:
        logger.error(f"Failed to update status for proposal {proposal_id} in {filepath}: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply accepted proposals to the rulebook.")
    parser.add_argument("--override-rule-lock", action="store_true", 
                        help="Apply proposals even if they target a locked rule (for testing).")
    args = parser.parse_args()

    logger.info("--- Starting Proposal Application Process ---")

    # 1. Load Rules (including locked status)
    rules = load_rules_from_rulebook()
    if not rules: 
        logger.warning("Could not load rules. Rule conflict checking will be skipped.")
        # Decide if we should exit or proceed without checks

    # 2. Load Proposals
    proposals = parse_proposals()
    accepted_proposals = [p for p in proposals if p['status'] == STATUS_ACCEPTED]

    if not accepted_proposals:
        logger.info("No accepted proposals found to apply.")
        exit(0)

    logger.info(f"Found {len(accepted_proposals)} accepted proposals to process.")

    # 3. Load current rulebook content
    try:
        current_rulebook_content = RULEBOOK_PATH.read_text(encoding='utf-8')
        original_rulebook_content = current_rulebook_content # Keep copy
    except FileNotFoundError:
        logger.error(f"Rulebook file not found at {RULEBOOK_PATH}. Cannot apply proposals.")
        exit(1)
    except Exception as e:
        logger.error(f"Error reading rulebook {RULEBOOK_PATH}: {e}")
        exit(1)
        
    applied_count = 0
    blocked_count = 0
    error_count = 0

    # 4. Process and Apply Accepted Proposals
    for proposal in accepted_proposals:
        proposal_id = proposal["id"]
        target_rule_id = proposal.get("target_rule_id")
        apply_proposal = True
        block_reason = ""
        
        # --- >>> Rule Conflict Check (coord-003) <<< ---
        if target_rule_id and target_rule_id != "new_rule" and rules:
            target_rule = rules.get(target_rule_id)
            if target_rule and target_rule.get("locked", False):
                if args.override_rule_lock:
                    logger.warning(f"Proposal {proposal_id} targets locked rule {target_rule_id}, but override flag is set. Proceeding.")
                else:
                    logger.error(f"Proposal {proposal_id} targets locked rule {target_rule_id}. Blocking application.")
                    apply_proposal = False
                    block_reason = f"Target rule {target_rule_id} is locked."
                    blocked_count += 1
            elif not target_rule:
                 logger.warning(f"Proposal {proposal_id} targets rule {target_rule_id} which was not found in the rulebook during initial load. Allowing application cautiously.")
        # --- End Rule Conflict Check ---

        if apply_proposal:
            try:
                # Apply the change to the content string
                current_rulebook_content = apply_proposal_to_rulebook(proposal, current_rulebook_content)
                # Update proposal status in the proposal file
                update_proposal_status_in_file(proposal_id, STATUS_APPLIED, "Applied successfully.")
                applied_count += 1
            except Exception as e:
                logger.error(f"Failed to apply proposal {proposal_id}: {e}", exc_info=True)
                # Update status to error
                update_proposal_status_in_file(proposal_id, STATUS_ERROR_APPLYING, f"Error during application: {e}")
                error_count += 1
        else:
            # Update status to blocked
            update_proposal_status_in_file(proposal_id, STATUS_BLOCKED_BY_RULE, block_reason)

    # 5. Write updated rulebook if changes were made
    if applied_count > 0:
        try:
            RULEBOOK_PATH.write_text(current_rulebook_content, encoding='utf-8')
            logger.info(f"Successfully wrote updated rulebook to {RULEBOOK_PATH}.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to write updated rulebook to {RULEBOOK_PATH}: {e}")
            # Consider recovery or alternative action here
            error_count += 1 # Count write failure as an error

    logger.info("--- Proposal Application Process Finished ---")
    logger.info(f"Summary: Applied={applied_count}, Blocked={blocked_count}, Errors={error_count}")

    if error_count > 0:
        exit(1) 