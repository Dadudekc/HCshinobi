"""Cursor result listener service.

This service monitors a directory for prompt files, processes them through Cursor,
and handles the results with robust error handling and retry logic.
"""

import os
import sys
import time
import json
import logging
import shutil
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from prometheus_client import Counter, Gauge, start_http_server
from typing import Optional, Dict, Any

from core.utils.system import DirectoryMonitor, FileManager, CommandExecutor
from core.coordination.config_service import ConfigService, ConfigFormat

# --- Custom Exceptions ---
class CursorResultError(Exception):
    """Base exception for cursor result handling errors."""
    pass

class MalformedResponseError(CursorResultError):
    """Raised when cursor response doesn't match expected format."""
    def __init__(self, message, response_data=None):
        super().__init__(message)
        self.response_data = response_data

class RetryableError(CursorResultError):
    """Raised for errors that should trigger a retry."""
    def __init__(self, message, retry_count=0, max_retries=3):
        super().__init__(message)
        self.retry_count = retry_count
        self.max_retries = max_retries

class FileOriginError(CursorResultError):
    """Raised when there are issues with file origin metadata."""
    def __init__(self, message, file_path=None, metadata=None):
        super().__init__(message)
        self.file_path = file_path
        self.metadata = metadata

# --- Path Setup --- 
# Add project root to sys.path to allow importing dreamforge modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------

# Attempt to import central logging; provide fallback
try:
    from dreamforge.core.governance_memory_engine import log_event
except ImportError:
    logging.warning("Could not import log_event from governance_memory_engine. Falling back to local logging only.")
    # Basic fallback implementation for log_event
    def log_event(event_type, agent_source, details):
        logging.info(f"[FALLBACK_LOG_EVENT] Type: {event_type}, Source: {agent_source}, Details: {details}")
        return True # Assume success

# Initialize config service
config_service = ConfigService(Path(__file__).parent.parent)
config_service.add_source(
    "config/cursor.yaml",
    ConfigFormat.YAML,
    namespace="cursor",
    required=False
)
config_service.add_source(
    ".env",
    ConfigFormat.ENV,
    required=False
)
config_service.load()

# Configuration with fallbacks
LISTENER_AGENT_ID = "CursorResultListener"
POLL_INTERVAL = config_service.get("cursor.poll_interval", 5)
METRICS_PORT = config_service.get("cursor.metrics_port", 8000)

# --- Logging Setup --- 
# Use configured LOG_FILE
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config_service.get("cursor.log_file", os.path.join(project_root, "_agent_coordination", "logs", "cursor_listener.log"))),
        logging.StreamHandler(sys.stdout)
    ]
)

# Log final configured paths
logging.info(f"--- Listener Configuration ---")
logging.info(f"PENDING_DIR: {config_service.get('cursor.pending_dir', os.path.join(project_root, "_agent_coordination", "prompt_queue", "cursor_pending"))}")
logging.info(f"PROCESSING_DIR: {config_service.get('cursor.processing_dir', os.path.join(project_root, "_agent_coordination", "prompt_queue", "cursor_processing"))}")
logging.info(f"ARCHIVE_DIR: {config_service.get('cursor.archive_dir', os.path.join(project_root, "_agent_coordination", "prompt_queue", "cursor_archive"))}")
logging.info(f"ERROR_DIR: {config_service.get('cursor.error_dir', os.path.join(project_root, "_agent_coordination", "prompt_queue", "cursor_error"))}")
logging.info(f"FEEDBACK_DIR: {config_service.get('cursor.feedback_dir', os.path.join(project_root, "_agent_coordination", "feedback_queue", "chatgpt_pending"))}")
logging.info(f"CONTEXT_FILE: {config_service.get('cursor.context_file', os.path.join(project_root, "_agent_coordination", "chatgpt_project_context.json"))}")
logging.info(f"LOG_FILE: {config_service.get('cursor.log_file', os.path.join(project_root, "_agent_coordination", "logs", "cursor_listener.log"))}")
logging.info(f"POLL_INTERVAL: {POLL_INTERVAL}s")
logging.info(f"AGENT_ID: {LISTENER_AGENT_ID}")
logging.info(f"-----------------------------")

# --- Prometheus Metrics ---
# Execution metrics
EXECUTION_COUNTER = Counter('cursor_execution_results', 
                          'Execution success/failure count',
                          ['status', 'source_agent'])

ERROR_COUNTER = Counter('cursor_error_types',
                       'Types of cursor failures',
                       ['error_type', 'source_agent'])

RETRY_COUNTER = Counter('cursor_retry_attempts',
                       'Number of retry attempts',
                       ['source_agent'])

FEEDBACK_COUNTER = Counter('cursor_feedback_processed',
                         'Number of feedback messages processed',
                         ['feedback_type', 'source_agent'])

# Performance metrics
PROCESSING_TIME = Gauge('cursor_processing_duration_seconds',
                       'Time taken to process prompts',
                       ['source_agent'])

QUEUE_SIZE = Gauge('cursor_queue_size',
                  'Number of items in various queues',
                  ['queue_type'])

class CursorResultListener(DirectoryMonitor):
    """Monitors and processes Cursor prompt files."""
    
    def __init__(self):
        project_root = Path(__file__).parent.parent
        
        # Initialize directories from config with fallbacks
        self.pending_dir = Path(config_service.get(
            "cursor.pending_dir",
            project_root / "_agent_coordination/prompt_queue/cursor_pending"
        ))
        self.processing_dir = Path(config_service.get(
            "cursor.processing_dir",
            project_root / "_agent_coordination/prompt_queue/cursor_processing"
        ))
        self.archive_dir = Path(config_service.get(
            "cursor.archive_dir",
            project_root / "_agent_coordination/prompt_queue/cursor_archive"
        ))
        self.error_dir = Path(config_service.get(
            "cursor.error_dir",
            project_root / "_agent_coordination/prompt_queue/cursor_error"
        ))
        self.feedback_dir = Path(config_service.get(
            "cursor.feedback_dir",
            project_root / "_agent_coordination/feedback_queue/chatgpt_pending"
        ))
        self.context_file = Path(config_service.get(
            "cursor.context_file",
            project_root / "_agent_coordination/chatgpt_project_context.json"
        ))
        
        # Initialize base class
        super().__init__(
            watch_dir=self.pending_dir,
            success_dir=self.archive_dir,
            error_dir=self.error_dir,
            file_pattern="*.json",
            poll_interval=POLL_INTERVAL
        )
        
        # Initialize utilities
        self.file_manager = FileManager(max_retries=3)
        self.command_executor = CommandExecutor(max_retries=3)
        
        # Create required directories
        for directory in [self.pending_dir, self.processing_dir,
                         self.archive_dir, self.error_dir,
                         self.feedback_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
    async def read_context_file(self) -> dict:
        """Read the project context file with retry support."""
        try:
            if self.context_file.exists():
                content = await self.file_manager.safe_read(self.context_file)
                if not content.strip():
                    logging.warning(f"Context file {self.context_file} is empty. Returning default context.")
                    return {"last_updated": None, "cursor_results": {}}
                return json.loads(content)
            else:
                logging.warning(f"Context file {self.context_file} not found. Returning default context.")
                return {"last_updated": None, "cursor_results": {}} # Default structure
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from context file {self.context_file}: {e}. Returning default context.")
            return {"last_updated": None, "cursor_results": {}}
        except Exception as e:
            logging.error(f"Error reading context file {self.context_file}: {e}. Returning default context.")
            return {"last_updated": None, "cursor_results": {}}
            
    async def write_context_file(self, data: dict) -> bool:
        """Write to the project context file with retry support."""
        try:
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            await self.file_manager.safe_write(
                self.context_file,
                json.dumps(data, indent=2)
            )
            logging.info(f"Successfully updated context file: {self.context_file}")
            return True
        except Exception as e:
            logging.error(f"Error writing to context file {self.context_file}: {e}")
            log_event("CONTEXT_WRITE_ERROR", LISTENER_AGENT_ID, {"file": self.context_file, "error": str(e)})
            return False

    async def update_context_with_result(self,
                                       prompt_id: str,
                                       cursor_result: dict,
                                       source_filename: str) -> dict:
        """Update the shared context file with Cursor result details."""
        logging.info(f"Updating context file for prompt_id: {prompt_id}")
        context_data = await self.read_context_file()
        
        if "cursor_results" not in context_data:
            context_data["cursor_results"] = {}
            
        result_summary = {
            "timestamp_processed_utc": datetime.now(timezone.utc).isoformat(),
            "status": cursor_result.get("status", "unknown"),
            "source_prompt_file": source_filename,
        }
        
        if cursor_result.get("status") == "success":
            result_summary["output_snippet"] = str(cursor_result.get("output", ""))[:250]
            result_summary["output_files"] = cursor_result.get("output_files", [])
        else:
            result_summary["error_message"] = str(cursor_result.get("error_message", ""))[:500]
            
        context_data["cursor_results"][prompt_id] = result_summary
        await self.write_context_file(context_data)
        return result_summary
        
    async def send_feedback(self,
                          prompt_id: str,
                          source_agent: str,
                          originating_request_id: Optional[str],
                          cursor_result: dict,
                          result_summary: dict) -> bool:
        """Send feedback to ChatGPT queue."""
        feedback_id = str(uuid.uuid4())
        feedback_payload = {
            "feedback_id": feedback_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "target_agent": source_agent,
            "prompt_id": prompt_id,
            "originating_request_id": originating_request_id,
            "cursor_result_status": cursor_result.get("status", "unknown"),
            "cursor_result_summary": result_summary,
            "source_listener": LISTENER_AGENT_ID
        }
        
        feedback_filename = (f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                           f"_{feedback_id}.json")
        feedback_filepath = self.feedback_dir / feedback_filename
        
        try:
            await self.file_manager.safe_write(
                feedback_filepath,
                json.dumps(feedback_payload, indent=2)
            )
            logging.info(f"Feedback message {feedback_id} for prompt {prompt_id} sent to {self.feedback_dir}")
            log_event("FEEDBACK_SENT", LISTENER_AGENT_ID, {"feedback_id": feedback_id, "prompt_id": prompt_id, "target_agent": source_agent})
            return True
        except Exception as e:
            logging.error(f"Failed to write feedback message {feedback_id} to {feedback_filepath}: {e}")
            log_event("FEEDBACK_ERROR", LISTENER_AGENT_ID, {"feedback_id": feedback_id, "prompt_id": prompt_id, "error": str(e)})
            # Should this cause the main processing to fail?
            return False

    async def process_file(self, file_path: Path) -> bool:
        """Process a single prompt file."""
        prompt_id = "UNKNOWN_ID"
        source_agent = "UNKNOWN_AGENT"
        originating_request_id = None
        
        try:
            # Move to processing directory
            processing_path = self.processing_dir / file_path.name
            await self.file_manager.safe_move(file_path, processing_path)
            
            # Read and parse prompt file
            content = await self.file_manager.safe_read(processing_path)
            prompt_data = json.loads(content)
            
            # Extract metadata
            prompt_id = prompt_data.get("prompt_id", file_path.stem)
            prompt_text = prompt_data.get("prompt_text", "")
            source_agent = prompt_data.get("source_agent", "UNKNOWN_AGENT")
            target_context = prompt_data.get("target_context", {})
            metadata = prompt_data.get("metadata", {})
            originating_request_id = metadata.get("originating_request_id")
            
            # Process through Cursor
            with PROCESSING_TIME.labels(source_agent=source_agent).time():
                # TODO: Replace with actual Cursor API integration
                # This is a simulation for now
                cursor_result = {
                    "status": "success",
                    "output": f"Simulated result for {prompt_id}",
                    "output_files": ["/path/simulated/output.py"]
                }
                
            # Update context and send feedback
            result_summary = await self.update_context_with_result(
                prompt_id,
                cursor_result,
                file_path.name
            )
            
            await self.send_feedback(
                prompt_id,
                source_agent,
                originating_request_id,
                cursor_result,
                result_summary
            )
            
            return cursor_result.get("status") == "success"
            
        except Exception as e:
            logging.error(f"Error processing {file_path.name}: {e}")
            return False
            
    def update_queue_metrics(self):
        """Update Prometheus metrics for queue sizes."""
        QUEUE_SIZE.labels(queue_type="pending").set(
            len(list(self.pending_dir.glob("*.json")))
        )
        QUEUE_SIZE.labels(queue_type="processing").set(
            len(list(self.processing_dir.glob("*.json")))
        )
        QUEUE_SIZE.labels(queue_type="archive").set(
            len(list(self.archive_dir.glob("*.json")))
        )
        QUEUE_SIZE.labels(queue_type="error").set(
            len(list(self.error_dir.glob("*.json")))
        )

async def main():
    """Main entry point."""
    # Start metrics server
    start_http_server(METRICS_PORT)
    logging.info(f"Started metrics server on port {METRICS_PORT}")
    
    # Create and start listener
    listener = CursorResultListener()
    await listener.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Listener stopped by user (KeyboardInterrupt).")
        log_event("AGENT_STOP", LISTENER_AGENT_ID, {"reason": "KeyboardInterrupt"})
    except Exception as e:
         logging.critical(f"Listener terminated due to unhandled exception: {e}")
         log_event("AGENT_CRASH", LISTENER_AGENT_ID, {"error": f"Unhandled exception: {e}"})
         sys.exit(1)
    sys.exit(0) 