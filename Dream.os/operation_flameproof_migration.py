import os
import shutil
import logging
from pathlib import Path

# --- Configuration ---
# Define the root directory of the project relative to the script location
# Assuming this script is run from the project root (D:\Dream.os)
PROJECT_ROOT = Path(__file__).parent.resolve()

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
        # Optionally add a FileHandler here
        # logging.FileHandler("migration_log.txt")
    ]
)
logger = logging.getLogger("FlameproofMigration")

# --- File Move & Directory Creation Definitions ---
# Based on PHASE 1 and PHASE 7 of FLAMEPROOF PROTOCOL
# Format: "relative/path/from/root": "relative/path/to/root"

# Directories to ensure exist before moving files into them
# Order matters if directories are nested
CREATE_DIRS = [
    "core",
    "core/coordination",
    "core/memory",
    "core/templates",
    "core/utils",
    "agents",
    "agents/base", # For BaseAgent later
    "agents/planner",
    "agents/workflow",
    "agents/reflection",
    "agents/social",
    "agents/calendar",
    "agents/cursor",
    "agents/recovery", # Renamed from stall_recovery
    "agents/meta", # For architects_edge
    "agents/integrations", # For chatgpt_commander
    "services",
    "services/cursor",
    "gui",
    "gui/tabs",
    "tests", # Root tests dir
    # Add subdirs for tests as needed, maybe handled by moves later
    "tests/core",
    "tests/agents",
]

# Files/Directories to move. Use os.rename which is generally safer against overwrites.
# Ensure target directory exists (handled by CREATE_DIRS).
MOVE_MAP = {
    # Core consolidation
    "_agent_coordination/core/agent_bus.py": "core/coordination/agent_bus.py", # Assuming this is the canonical one
    "_agent_coordination/core/bus_types.py": "core/coordination/bus_types.py", # Move related files
    "_agent_coordination/core/agent_registry.py": "core/coordination/agent_registry.py", # Move related files
    "_agent_coordination/core/system_diagnostics.py": "core/coordination/system_diagnostics.py", # Move related files
    "_agent_coordination/core/shutdown_coordinator.py": "core/coordination/shutdown_coordinator.py", # Move related files
    "_agent_coordination/dispatchers": "core/coordination/dispatchers", # Move dispatchers directory
    "coordination/agent_bus.py": None, # Mark for deletion/ignore later if needed, canonical one moved above
    "dreamforge/core/agent_bus.py": None, # Mark for deletion/ignore later if needed
    "dreamforge/core/template_engine.py": "core/templates/template_engine.py",
    "utils": "core/utils_to_merge", # Rename old utils, manual merge needed later
    "_agent_coordination/core/utils.py": "core/utils/coordination_utils.py", # Move specific utils if exist
    "core/config.py": "core/config.py", # Stays, but ensure it's the only one later
    "dreamforge/core/config.py": None, # Mark for deletion/ignore later
    "agents/config.py": None, # Mark for deletion/ignore later
    "core/memory": "core/memory_to_merge", # Rename old memory, manual merge needed later
    "_agent_coordination/memory": "core/memory/coordination_memory", # Move specific memory if exists
    "_agent_coordination/templates": "core/templates/coordination_templates", # Move specific templates

    # GUI consolidation
    "core/gui": "gui", # Move the whole GUI directory from core

    # Agents consolidation (moving specific files/dirs)
    "_agent_coordination/agents/cursor_control_agent.py": "agents/cursor/control_agent.py",
    "_agent_coordination/agents/stall_recovery_agent.py": "agents/recovery/stall_agent.py",
    "agents/agents/reflection_agent/reflection_agent.py": "agents/reflection/agent.py", # Flatten agents/agents
    "agents/calendar_agent.py": "agents/calendar/agent.py",
    "agents/architects_edge_agent.py": "agents/meta/architects_edge.py",
    "agents/chatgpt_commander_agent.py": "agents/integrations/chatgpt_commander.py",
    "agents/social": "agents/social", # Keep social under agents
    "agents/services": "services/agent_services", # Move agent-specific services
    "agents/memory": "core/memory/agent_memory", # Move agent-specific memory to core/memory
    # Note: Need to handle specific agent moves from dreamforge/agents later if needed

    # Services consolidation
    "core/coordination/cursor/cursor_window_controller.py": "services/cursor/window_controller.py",
    "_agent_coordination/ui_controllers": "services/ui_controllers", # Move UI controllers

    # Tools consolidation - might need manual review
    # Moving supervisor tools under core for now? Or keep separate? Let's move to core/tools
    "_agent_coordination/supervisor_tools": "core/tools/supervisor",
    "_agent_coordination/tools": "core/tools/coordination",
    "tools": "core/tools_to_merge", # Rename old tools, manual merge later

    # Runtime consolidation - move under core?
    "_agent_coordination/runtime": "core/runtime",

    # Root level files consolidation
    "governance_scraper.py": "core/tools/scrapers/governance_scraper.py", # Example move
    "chat_scraper_dispatcher.py": "core/tools/scrapers/chat_scraper_dispatcher.py", # Example move

    # Delete placeholder/redundant top-level directories (do this *after* moving contents)
    "_core": None, # Mark for deletion if empty later
    "_agent_coordination": None, # Mark for deletion if empty later
    "coordination": None, # Mark for deletion if empty later

    # Test consolidation requires manual merging, just ensure root `tests` exists
    # Add specific test file moves if straightforward
    "core/tests": None, # Mark for deletion/manual merge
    "dreamforge/tests": None, # Mark for deletion/manual merge
}

# --- Migration Logic ---

def migrate_structure():
    logger.info("--- Starting FLAMEPROOF PROTOCOL Migration ---")
    logger.info(f"Project Root: {PROJECT_ROOT}")

    # 1. Create target directories
    logger.info("Creating target directories...")
    for dir_rel_path in CREATE_DIRS:
        target_dir = PROJECT_ROOT / dir_rel_path
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {target_dir}")
        except OSError as e:
            logger.error(f"Failed to create directory {target_dir}: {e}", exc_info=True)
            # Decide if this is fatal or if we should continue
            # For now, continue but log error

    # 2. Move files and directories
    logger.info("Moving files and directories...")
    moved_count = 0
    skipped_count = 0
    error_count = 0
    delete_candidates = []

    for src_rel, dest_rel in MOVE_MAP.items():
        source_path = PROJECT_ROOT / src_rel
        logger.debug(f"Processing mapping: '{src_rel}' -> '{dest_rel}'")

        if not source_path.exists():
            logger.warning(f"Source path does not exist, skipping: {source_path}")
            skipped_count += 1
            continue

        if dest_rel is None:
            logger.info(f"Marking for potential deletion (or manual review): {source_path}")
            delete_candidates.append(source_path)
            continue

        target_path = PROJECT_ROOT / dest_rel

        # Ensure target directory exists *just before* moving
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
             logger.error(f"Failed to ensure target parent directory {target_path.parent} for {source_path}: {e}. Skipping move.")
             error_count += 1
             continue


        # Check if target already exists (os.rename usually fails, safety check)
        if target_path.exists():
             logger.warning(f"Target path {target_path} already exists. Skipping move for {source_path}. Manual merge likely required.")
             skipped_count += 1
             continue

        # Perform the move using os.rename
        try:
            os.rename(source_path, target_path)
            logger.info(f"Moved: {source_path} -> {target_path}")
            moved_count += 1
        except OSError as e:
            logger.error(f"Failed to move {source_path} to {target_path}: {e}", exc_info=True)
            error_count += 1

    # 3. Report Summary
    logger.info("--- Migration Summary ---")
    logger.info(f"Files/Directories Moved: {moved_count}")
    logger.info(f"Mappings Skipped (Source missing or Target exists): {skipped_count}")
    logger.info(f"Errors during move: {error_count}")
    if delete_candidates:
         logger.warning("The following paths were marked for potential deletion/review (ensure contents were moved/merged):")
         for path in delete_candidates:
             logger.warning(f" - {path}")

    if error_count > 0:
        logger.error("Migration completed with errors. Please review logs.")
    else:
        logger.info("Migration script completed.")
    logger.info("--- NOTE: Import paths within moved files will likely be broken until refactored. ---")

if __name__ == "__main__":
    migrate_structure()
