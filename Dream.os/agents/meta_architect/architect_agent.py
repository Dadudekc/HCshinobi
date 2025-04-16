import threading
import traceback
import os
from datetime import datetime, timedelta, timezone

# Import config
from core import config

# Add project root to sys.path to allow importing core modules
# ... (path logic)

# Import from core
try:
    from core.memory.governance_memory_engine import log_event as log_governance_event
    gme_import_ok = True
except ImportError as e:
    print(f"[MetaArchitect] Error importing governance_memory_engine: {e}")
    gme_import_ok = False
    # Remove dummy fallback function definition
    # def log_governance_event(*args, **kwargs): 
    #     print("[MetaArchitect] FAKE log_governance_event called (GME import failed)")
    log_governance_event = None # Set to None if import fails

# Configuration
AGENT_ID = "meta_architect"
#RUNTIME_DIR_NAME = "runtime"
#ANALYSIS_DIR_NAME = "analysis"
#MEMORY_DIR_NAME = "memory"

# Construct paths relative to PROJECT_ROOT
#RUNTIME_DIR = os.path.join(project_root, RUNTIME_DIR_NAME)
#ANALYSIS_DIR = os.path.join(project_root, ANALYSIS_DIR_NAME)
#MEMORY_DIR = os.path.join(project_root, MEMORY_DIR_NAME)

# Updated paths - Use core.config instead
#PERFORMANCE_LOG_PATH = os.path.join(MEMORY_DIR, "performance_log.jsonl")
REFLECTION_LOG_PATTERN = os.path.join(config.LOG_DIR, "*", "reflection", "reflection_log.md") # Keep LOG_DIR base
#RULEBOOK_PATH = os.path.join(RUNTIME_DIR, "rulebook.md") # Canonical rulebook in runtime root
#REPORT_DIR = os.path.join(ANALYSIS_DIR, "architect_reports")
#PROPOSAL_FILE = os.path.join(ANALYSIS_DIR, "rulebook_update_proposals.md")
ANALYSIS_INTERVAL_HOURS = 24 # How often to run a full analysis cycle
RECENT_ERROR_THRESHOLD_HOURS = 72 # How far back to look for error patterns
FAILURE_RATE_THRESHOLD = 0.15 # e.g., 15% failure rate for an agent/task triggers attention
REPEATED_ERROR_COUNT = 3
AUTO_APPLY_HEADER = "\n## [AUTO-APPLIED RULES]\n" # Header for applied rules in rulebook

# Ensure output dirs exist (relative to project root)
# os.makedirs(REPORT_DIR, exist_ok=True)
# os.makedirs(MEMORY_DIR, exist_ok=True) # Ensure memory dir exists
# Use config paths for directory creation checks/creation if needed
os.makedirs(config.REPORT_DIR, exist_ok=True)
os.makedirs(config.MEMORY_DIR, exist_ok=True)

class ArchitectAgent:
    def __init__(self, analysis_interval_minutes=60):
        self.agent_id = AGENT_ID
        self.analysis_interval = timedelta(minutes=analysis_interval_minutes)
        self.stop_event = threading.Event()
        self.thread = None

        # Ensure log_governance_event is defined, even if import failed
        global log_governance_event
        if log_governance_event is None:
            print(f"[{AGENT_ID}] Warning: Governance Memory Engine not imported. Events will not be logged centrally.")
            # Remove the dummy function definition - rely on the None check or other handling
            # def dummy_log_event(etype, src, dtls):
            #      try: details_str = json.dumps(dtls)
            #      except: details_str = str(dtls)
            #      print(f"[DUMMY GME LOG] {etype} | {src} | {details_str}")
            # log_governance_event = dummy_log_event 

        # Log initialization using the potentially valid log_governance_event
        if gme_import_ok and log_governance_event:
             log_governance_event("AGENT_INITIALIZING", self.agent_id, {"interval_minutes": analysis_interval_minutes})

        self.performance_logs = self._load_performance_logs()
        self.reflection_entries = self._load_reflection_logs()

    def _load_performance_logs(self):
        logs = []
        if not os.path.exists(config.PERFORMANCE_LOG_FILE):
            if gme_import_ok and log_governance_event:
                 log_governance_event("AGENT_WARNING", self.agent_id, {"warning": "Performance log file not found", "path": config.PERFORMANCE_LOG_FILE})
            return logs
        try:
            with open(config.PERFORMANCE_LOG_FILE, 'r', encoding='utf-8') as f:
                # ...
        except Exception as e:
            if gme_import_ok and log_governance_event:
                log_governance_event("AGENT_ERROR", self.agent_id, {"error": "Failed to load performance logs", "path": config.PERFORMANCE_LOG_FILE, "details": str(e)})
        return logs

    def _load_reflection_logs(self):
        # ... uses REFLECTION_LOG_PATTERN (already updated)

    def _generate_system_report(self, clusters, gaps):
        # ...
        report_path = os.path.join(config.REPORT_DIR, f"system_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md")
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            # ...
        except Exception as e:
            if gme_import_ok and log_governance_event:
                log_governance_event("AGENT_ERROR", self.agent_id, {"error": "Error saving system report", "path": report_path, "details": str(e)})

    def _propose_rule_updates(self, clusters, gaps):
        # ...
        try:
            # ...
            with open(config.PROPOSAL_FILE, 'a+', encoding='utf-8') as f:
                # ...
        except Exception as e:
             if gme_import_ok and log_governance_event:
                log_governance_event("AGENT_ERROR", self.agent_id, {"error": "Error appending rule proposals", "path": config.PROPOSAL_FILE, "details": str(e)}) # Use logger
        # ...

    def _apply_ratified_proposals(self):
        # ...
        if not os.path.exists(config.PROPOSAL_FILE):
            # ...
            return
        if not os.path.exists(config.RULEBOOK_PATH):
            # ...
            return

        try:
            with open(config.PROPOSAL_FILE, 'r', encoding='utf-8') as f_prop:
                # ...
        except Exception as e_prop_read:
             if gme_import_ok and log_governance_event:
                 log_governance_event("AGENT_ERROR", self.agent_id, {"error": "Error reading proposal file", "path": config.PROPOSAL_FILE, "details": str(e_prop_read)}) # Use logger
             return
        # ...
        try:
            with open(config.RULEBOOK_PATH, 'a', encoding='utf-8') as f_rule:
                # ...
        except Exception as e_rule_write:
            if gme_import_ok and log_governance_event:
                 log_governance_event("AGENT_ERROR", self.agent_id, {"error": "Error applying rules to rulebook", "path": config.RULEBOOK_PATH, "details": str(e_rule_write)}) # Use logger
            # ...
        try:
            with open(config.PROPOSAL_FILE, 'w', encoding='utf-8') as f_prop_write:
                # ...
        except Exception as e_prop_write:
             if gme_import_ok and log_governance_event:
                 log_governance_event("AGENT_ERROR", self.agent_id, {"error": "Error rewriting proposal file", "path": config.PROPOSAL_FILE, "details": str(e_prop_write)}) # Use logger
        # ... 