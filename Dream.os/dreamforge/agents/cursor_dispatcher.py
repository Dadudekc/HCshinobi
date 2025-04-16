import logging
import time
from pathlib import Path
from typing import Dict, Optional, Any
from queue import Queue

from dreamforge.core.enums.task_types import TaskType
from dreamforge.core.agent_bus import AgentBus
from dreamforge.core.prompt_staging_service import stage_and_execute_prompt

logger = logging.getLogger(__name__)

class CursorDispatcher:
    """
    Handles execution of Cursor tasks and communication with the agent bus.
    Acts as a bridge between ChatGPT and Cursor operations.
    """
    
    def __init__(self):
        self.agent_bus = AgentBus()
        self.task_queue = Queue()
        self.is_running = False
        self.current_task: Optional[Dict] = None
        
    def execute_cursor_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single Cursor task and returns the result.
        
        Args:
            task: Dictionary containing task details
                {
                    "id": str,
                    "type": TaskType,
                    "payload": Dict[str, Any],
                    "metadata": Dict[str, Any]
                }
                
        Returns:
            Dict containing execution result and metadata
        """
        try:
            task_type = TaskType(task["type"])
            logger.info(f"Executing Cursor task: {task_type}")
            
            result = {
                "success": False,
                "error": None,
                "data": None,
                "metadata": {}
            }
            
            if task_type == TaskType.GENERATE_TESTS:
                result = self._handle_test_generation(task["payload"])
            elif task_type == TaskType.FIX_CODE:
                result = self._handle_code_fix(task["payload"])
            elif task_type == TaskType.ANALYZE_FILE:
                result = self._handle_file_analysis(task["payload"])
            else:
                result["error"] = f"Unsupported task type: {task_type}"
                
            return result
            
        except Exception as e:
            logger.error(f"Error executing Cursor task: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "metadata": {"exception_type": type(e).__name__}
            }
            
    def _handle_test_generation(self, payload: Dict) -> Dict:
        """Handles test generation tasks."""
        target_file = payload.get("target_file")
        description = payload.get("description")
        
        if not target_file or not description:
            return {
                "success": False,
                "error": "Missing required fields: target_file or description"
            }
            
        try:
            # Use prompt staging service to generate test code
            test_code = stage_and_execute_prompt(
                agent_id="Cursor",
                task_type=TaskType.GENERATE_TESTS,
                template_name="generate_tests.jinja",
                input_data={"description": description, "target_file": target_file}
            )
            
            # Write test code to file
            test_file = Path(target_file)
            test_dir = test_file.parent / "tests"
            test_dir.mkdir(exist_ok=True)
            
            test_file_path = test_dir / f"test_{test_file.stem}.py"
            test_file_path.write_text(test_code)
            
            return {
                "success": True,
                "data": {
                    "test_file": str(test_file_path),
                    "test_code": test_code
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Test generation failed: {str(e)}"
            }
            
    def _handle_code_fix(self, payload: Dict) -> Dict:
        """Handles code fix tasks."""
        file_path = payload.get("file_path")
        issue_description = payload.get("issue_description")
        
        if not file_path or not issue_description:
            return {
                "success": False,
                "error": "Missing required fields: file_path or issue_description"
            }
            
        try:
            # Use prompt staging service to generate fix
            fix_result = stage_and_execute_prompt(
                agent_id="Cursor",
                task_type=TaskType.FIX_CODE,
                template_name="fix_code.jinja",
                input_data={
                    "file_path": file_path,
                    "issue_description": issue_description
                }
            )
            
            return {
                "success": True,
                "data": fix_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Code fix failed: {str(e)}"
            }
            
    def _handle_file_analysis(self, payload: Dict) -> Dict:
        """Handles file analysis tasks."""
        file_path = payload.get("file_path")
        analysis_type = payload.get("analysis_type", "general")
        
        if not file_path:
            return {
                "success": False,
                "error": "Missing required field: file_path"
            }
            
        try:
            # Use prompt staging service for analysis
            analysis_result = stage_and_execute_prompt(
                agent_id="Cursor",
                task_type=TaskType.ANALYZE_FILE,
                template_name="analyze_file.jinja",
                input_data={
                    "file_path": file_path,
                    "analysis_type": analysis_type
                }
            )
            
            return {
                "success": True,
                "data": analysis_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"File analysis failed: {str(e)}"
            }
            
    def run_dispatcher_loop(self):
        """
        Main loop that polls for tasks and executes them.
        """
        self.is_running = True
        logger.info("Starting Cursor dispatcher loop")
        
        while self.is_running:
            try:
                # Check for new tasks
                task = self.agent_bus.claim_task(agent_id="Cursor")
                
                if task:
                    self.current_task = task
                    result = self.execute_cursor_task(task)
                    
                    # Send result back through agent bus
                    self.agent_bus.complete_task(
                        task_id=task["id"],
                        result=result,
                        metadata={
                            "completed_at": time.time(),
                            "agent_id": "Cursor"
                        }
                    )
                    
                    # If task was from ChatGPT, send response back
                    if task.get("source_agent") == "ChatGPT":
                        self.agent_bus.send_task(
                            to="ChatGPT",
                            task_type=TaskType.RESULT_DELIVERY,
                            payload=result
                        )
                        
                    self.current_task = None
                    
                time.sleep(1)  # Prevent tight loop
                
            except Exception as e:
                logger.error(f"Error in dispatcher loop: {e}", exc_info=True)
                time.sleep(5)  # Back off on error
                
    def stop(self):
        """Stops the dispatcher loop."""
        self.is_running = False
        logger.info("Stopping Cursor dispatcher") 