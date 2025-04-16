"""CursorExecutorAgent - Executes prompts using the Cursor API."""

import logging
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime

from dreamos.agents import PromptPlan, ExecutionResult

logger = logging.getLogger(__name__)

class CursorExecutorAgent:
    """Agent responsible for executing prompts through Cursor."""
    
    def __init__(self, workspace_dir: str, results_dir: str = "queue/results"):
        """Initialize the CursorExecutorAgent.
        
        Args:
            workspace_dir: Directory containing the workspace files
            results_dir: Directory for storing execution results
        """
        self.workspace_dir = Path(workspace_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    async def execute_prompt(self, prompt: PromptPlan, max_retries: int = 3) -> ExecutionResult:
        """Execute a prompt through Cursor.
        
        Args:
            prompt: PromptPlan object to execute
            max_retries: Maximum number of retry attempts
            
        Returns:
            ExecutionResult object containing execution details
        """
        start_time = time.time()
        retry_count = 0
        error_msg = None
        
        while retry_count < max_retries:
            try:
                # Get file contents before changes
                original_contents = self._read_files(prompt.file_targets)
                
                # Execute prompt through Cursor
                cursor_response = await self._send_to_cursor(prompt)
                
                # Apply changes and validate
                diff = self._apply_changes(cursor_response, prompt.file_targets)
                validation = self._validate_changes(prompt)
                
                execution_time = time.time() - start_time
                
                result = ExecutionResult(
                    prompt_id=prompt.prompt_id,
                    task_id=prompt.task_id,
                    status="completed" if validation["success"] else "failed",
                    diff=diff,
                    execution_time=execution_time,
                    retry_attempts=retry_count,
                    error_message=None,
                    validation_results=validation
                )
                
                self._save_result(result)
                return result
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                logger.warning(f"Execution attempt {retry_count} failed: {e}")
                time.sleep(2 ** retry_count)  # Exponential backoff
        
        # All retries failed
        failure_result = ExecutionResult(
            prompt_id=prompt.prompt_id,
            task_id=prompt.task_id,
            status="error",
            diff=None,
            execution_time=time.time() - start_time,
            retry_attempts=retry_count,
            error_message=error_msg,
            validation_results={"success": False, "errors": [error_msg]}
        )
        
        self._save_result(failure_result)
        return failure_result
    
    def _read_files(self, file_paths: List[str]) -> Dict[str, str]:
        """Read contents of target files.
        
        Args:
            file_paths: List of file paths to read
            
        Returns:
            Dict mapping file paths to their contents
        """
        contents = {}
        for path in file_paths:
            try:
                full_path = self.workspace_dir / path
                if full_path.exists():
                    contents[path] = full_path.read_text()
            except Exception as e:
                logger.error(f"Failed to read file {path}: {e}")
        return contents
    
    async def _send_to_cursor(self, prompt: PromptPlan) -> Dict:
        """Send prompt to Cursor API.
        
        Args:
            prompt: PromptPlan object to execute
            
        Returns:
            Cursor API response
        """
        # TODO: Implement actual Cursor API integration
        # This is a placeholder that simulates the API response
        return {
            "success": True,
            "changes": [
                {
                    "file": file_path,
                    "diff": f"Simulated changes for {file_path}"
                }
                for file_path in prompt.file_targets
            ]
        }
    
    def _apply_changes(self, cursor_response: Dict, file_targets: List[str]) -> str:
        """Apply changes from Cursor response.
        
        Args:
            cursor_response: Response from Cursor API
            file_targets: List of target files
            
        Returns:
            Combined diff of all changes
        """
        if not cursor_response.get("success"):
            raise ValueError("Cursor response indicates failure")
            
        combined_diff = []
        for change in cursor_response.get("changes", []):
            file_path = change.get("file")
            if file_path in file_targets:
                # TODO: Implement actual file modification logic
                combined_diff.append(change.get("diff", ""))
                
        return "\n".join(combined_diff)
    
    def _validate_changes(self, prompt: PromptPlan) -> Dict:
        """Validate applied changes.
        
        Args:
            prompt: PromptPlan object that was executed
            
        Returns:
            Validation results dictionary
        """
        # TODO: Implement actual validation logic
        return {
            "success": True,
            "tests_run": 0,
            "tests_passed": 0,
            "linting_errors": [],
            "warnings": []
        }
    
    def _save_result(self, result: ExecutionResult) -> None:
        """Save execution result to file.
        
        Args:
            result: ExecutionResult object to save
        """
        result_file = self.results_dir / f"result_{result.prompt_id}.json"
        try:
            with open(result_file, 'w') as f:
                json.dump(
                    {
                        "prompt_id": result.prompt_id,
                        "task_id": result.task_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": result.status,
                        "diff": result.diff,
                        "execution_time": result.execution_time,
                        "retry_attempts": result.retry_attempts,
                        "error_message": result.error_message,
                        "validation_results": result.validation_results
                    },
                    f,
                    indent=2
                )
            logger.info(f"Saved execution result for prompt {result.prompt_id}")
        except Exception as e:
            logger.error(f"Failed to save execution result: {e}")
    
    def get_result(self, prompt_id: str) -> Optional[ExecutionResult]:
        """Load execution result for a prompt.
        
        Args:
            prompt_id: ID of the prompt
            
        Returns:
            ExecutionResult object if found, None otherwise
        """
        result_file = self.results_dir / f"result_{prompt_id}.json"
        if not result_file.exists():
            return None
            
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                return ExecutionResult(**data)
        except Exception as e:
            logger.error(f"Failed to load execution result: {e}")
            return None 