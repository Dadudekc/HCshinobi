import sys
import os
import logging # Use logging for consistency

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
log = logging.getLogger('ImportTest')

# Calculate expected path
workspace_root = os.path.abspath(os.path.dirname(__file__))
log.info(f"WORKSPACE ROOT: {workspace_root}")

agents_dir_path = os.path.join(workspace_root, "agents")
log.info(f"AGENTS DIR PATH: {agents_dir_path}")
log.info(f"AGENTS DIR exists: {os.path.exists(agents_dir_path)}")
log.info(f"AGENTS DIR isdir: {os.path.isdir(agents_dir_path)}")
if os.path.exists(agents_dir_path) and os.path.isdir(agents_dir_path):
    try:
        log.info(f"Contents of AGENTS DIR: {os.listdir(agents_dir_path)}")
    except Exception as e:
        log.error(f"Could not list AGENTS DIR: {e}")

agents_core_path = os.path.join(agents_dir_path, "core")
log.info(f"AGENTS.CORE PATH: {agents_core_path}")
log.info(f"AGENTS.CORE PATH exists: {os.path.exists(agents_core_path)}")
log.info(f"AGENTS.CORE PATH isdir: {os.path.isdir(agents_core_path)}")
if os.path.exists(agents_core_path) and os.path.isdir(agents_core_path):
    try:
        log.info(f"Contents of AGENTS.CORE: {os.listdir(agents_core_path)}")
    except Exception as e:
        log.error(f"Could not list AGENTS.CORE: {e}")

# Add workspace root to sys.path explicitly
log.info(f"Original sys.path: {sys.path}")
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)
    log.info(f"Modified sys.path: {sys.path}")
else:
    log.info("Workspace root already in sys.path.")

try:
    log.info("Attempting import: from agents.core.agent_command_handler import CommandHandler")
    from agents.core.agent_command_handler import CommandHandler
    log.info("✅ SUCCESS: Import succeeded.")
except Exception as e:
    log.error("❌ ERROR during import:")
    import traceback
    traceback.print_exc() # Print full traceback to stderr
    sys.exit(1) # Exit with error code

log.info("Import test script finished.")
sys.exit(0) 