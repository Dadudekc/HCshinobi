import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

from dreamforge.core.agent_bus import AgentBus
from dreamforge.core.enums.task_types import TaskType
from dreamforge.core.prompt_staging_service import log_event

logger = logging.getLogger(__name__)

class ChatGPTCommander:
    """
    Dispatches tasks to Cursor from ChatGPT inputs or system goals.
    Handles task creation, dispatch, and response management.
    """

    def __init__(self):
        self.agent_id = "ChatGPT"
        self.agent_bus = AgentBus()
        self.pending_tasks: Dict[str, Dict] = {}
        
    def send_generate_tests_task(self, target_file: str, description: str, 
                               wait_for_response: bool = False, timeout: int = 300) -> Dict[str, Any]:
        """
        Constructs and sends a GENERATE_TESTS task to Cursor.
        
        Args:
            target_file: Path to the file needing tests
            description: Test requirements/description
            wait_for_response: Whether to wait for task completion
            timeout: Maximum time to wait for response (seconds)
            
        Returns:
            Dict containing task status and results if waited
        """
        task_payload = {
            "target_file": target_file,
            "description": description
        }

        task_id = self.agent_bus.send_task(
            to="Cursor",
            task_type=TaskType.GENERATE_TESTS,
            payload=task_payload,
            metadata={
                "origin": "ChatGPT",
                "timestamp": time.time()
            }
        )
        
        self.pending_tasks[task_id] = {
            "type": TaskType.GENERATE_TESTS,
            "status": "sent",
            "timestamp": time.time()
        }

        log_event("COMMANDER_TASK_SENT", self.agent_id, {
            "task_type": TaskType.GENERATE_TESTS,
            "task_id": task_id,
            "target_file": target_file
        })
        
        if wait_for_response:
            return self.wait_for_task_completion(task_id, timeout)
            
        return {"task_id": task_id, "status": "sent"}
        
    def send_code_fix_task(self, file_path: str, issue_description: str,
                          wait_for_response: bool = False, timeout: int = 300) -> Dict[str, Any]:
        """
        Sends a code fix task to Cursor.
        
        Args:
            file_path: Path to file needing fixes
            issue_description: Description of the issue to fix
            wait_for_response: Whether to wait for completion
            timeout: Maximum wait time in seconds
        """
        task_payload = {
            "file_path": file_path,
            "issue_description": issue_description
        }
        
        task_id = self.agent_bus.send_task(
            to="Cursor",
            task_type=TaskType.FIX_CODE,
            payload=task_payload,
            metadata={"origin": "ChatGPT"}
        )
        
        self.pending_tasks[task_id] = {
            "type": TaskType.FIX_CODE,
            "status": "sent",
            "timestamp": time.time()
        }
        
        log_event("COMMANDER_TASK_SENT", self.agent_id, {
            "task_type": TaskType.FIX_CODE,
            "task_id": task_id,
            "file_path": file_path
        })
        
        if wait_for_response:
            return self.wait_for_task_completion(task_id, timeout)
            
        return {"task_id": task_id, "status": "sent"}
        
    def send_analysis_task(self, file_path: str, analysis_type: str = "general",
                          wait_for_response: bool = False, timeout: int = 300) -> Dict[str, Any]:
        """
        Sends a file analysis task to Cursor.
        
        Args:
            file_path: Path to file to analyze
            analysis_type: Type of analysis to perform
            wait_for_response: Whether to wait for completion
            timeout: Maximum wait time in seconds
        """
        task_payload = {
            "file_path": file_path,
            "analysis_type": analysis_type
        }
        
        task_id = self.agent_bus.send_task(
            to="Cursor",
            task_type=TaskType.ANALYZE_FILE,
            payload=task_payload,
            metadata={"origin": "ChatGPT"}
        )
        
        self.pending_tasks[task_id] = {
            "type": TaskType.ANALYZE_FILE,
            "status": "sent",
            "timestamp": time.time()
        }
        
        log_event("COMMANDER_TASK_SENT", self.agent_id, {
            "task_type": TaskType.ANALYZE_FILE,
            "task_id": task_id,
            "file_path": file_path
        })
        
        if wait_for_response:
            return self.wait_for_task_completion(task_id, timeout)
            
        return {"task_id": task_id, "status": "sent"}
        
    def wait_for_task_completion(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Waits for a task to complete, polling the agent bus.
        
        Args:
            task_id: ID of task to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Dict containing task results or timeout status
        """
        start_time = time.time()
        poll_interval = 1.0  # Start with 1 second
        
        while time.time() - start_time < timeout:
            result = self.agent_bus.get_task_result(task_id)
            
            if result:
                self.pending_tasks[task_id]["status"] = "completed"
                self.pending_tasks[task_id]["result"] = result
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": result
                }
                
            time.sleep(poll_interval)
            # Exponential backoff up to 5 seconds
            poll_interval = min(poll_interval * 1.5, 5.0)
            
        # Timeout occurred
        self.pending_tasks[task_id]["status"] = "timeout"
        return {
            "task_id": task_id,
            "status": "timeout",
            "error": f"Task did not complete within {timeout} seconds"
        }
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Gets the current status of a task."""
        if task_id not in self.pending_tasks:
            return None
            
        task_info = self.pending_tasks[task_id].copy()
        
        # Check for completion if task was sent
        if task_info["status"] == "sent":
            result = self.agent_bus.get_task_result(task_id)
            if result:
                task_info["status"] = "completed"
                task_info["result"] = result
                self.pending_tasks[task_id].update(task_info)
                
        return task_info
        
    def get_pending_tasks(self) -> Dict[str, Dict]:
        """Returns all pending tasks and their current status."""
        return {
            task_id: self.get_task_status(task_id)
            for task_id in self.pending_tasks
        }
        
    def cleanup_old_tasks(self, max_age: int = 3600):
        """Removes tasks older than max_age seconds."""
        current_time = time.time()
        to_remove = []
        
        for task_id, task_info in self.pending_tasks.items():
            if current_time - task_info["timestamp"] > max_age:
                to_remove.append(task_id)
                
        for task_id in to_remove:
            del self.pending_tasks[task_id]
            
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks") 