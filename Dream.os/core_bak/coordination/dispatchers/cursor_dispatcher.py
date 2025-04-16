"""Unified Cursor dispatcher that handles both automated and UI-based interactions."""

import os
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import pyautogui
import pyperclip

from dreamforge.core.enums.task_types import TaskType
from dreamforge.core.prompt_staging_service import stage_and_execute_prompt
from .base_dispatcher import BaseDispatcher

class CursorDispatcher(BaseDispatcher):
    """
    Handles execution of Cursor tasks and communication with the agent bus.
    Supports both automated API calls and UI-based interactions.
    """
    
    def __init__(self, cursor_exe_path: Optional[str] = None):
        super().__init__()
        self.cursor_exe_path = cursor_exe_path or self._get_default_cursor_path()
        
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Cursor task based on its type."""
        try:
            task_type = task.get("type")
            if not task_type:
                return {"success": False, "error": "Missing task type"}
                
            if task_type == TaskType.GENERATE_TESTS:
                return self._handle_test_generation(task["payload"])
            elif task_type == TaskType.FIX_CODE:
                return self._handle_code_fix(task["payload"])
            elif task_type == TaskType.ANALYZE_FILE:
                return self._handle_file_analysis(task["payload"])
            elif task_type == TaskType.UI_INTERACTION:
                return self._handle_ui_interaction(task["payload"])
            else:
                return {"success": False, "error": f"Unsupported task type: {task_type}"}
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metadata": {"exception_type": type(e).__name__}
            }
            
    def _handle_test_generation(self, payload: Dict) -> Dict:
        """Handle test generation tasks using prompt staging."""
        target_file = payload.get("target_file")
        description = payload.get("description")
        
        if not target_file or not description:
            return {
                "success": False,
                "error": "Missing required fields: target_file or description"
            }
            
        try:
            test_code = stage_and_execute_prompt(
                agent_id="Cursor",
                task_type=TaskType.GENERATE_TESTS,
                template_name="generate_tests.jinja",
                input_data={"description": description, "target_file": target_file}
            )
            
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
        """Handle code fix tasks using prompt staging."""
        file_path = payload.get("file_path")
        issue_description = payload.get("issue_description")
        
        if not file_path or not issue_description:
            return {
                "success": False,
                "error": "Missing required fields: file_path or issue_description"
            }
            
        try:
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
        """Handle file analysis tasks using prompt staging."""
        file_path = payload.get("file_path")
        analysis_type = payload.get("analysis_type", "general")
        
        if not file_path:
            return {
                "success": False,
                "error": "Missing required field: file_path"
            }
            
        try:
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
            
    def _handle_ui_interaction(self, payload: Dict) -> Dict:
        """Handle UI-based interactions with Cursor."""
        prompt = payload.get("prompt")
        context_file = payload.get("context_file")
        
        if not prompt and not context_file:
            return {
                "success": False,
                "error": "Must provide either prompt or context_file"
            }
            
        try:
            # Load context if provided
            if context_file:
                context_path = Path(context_file)
                if not context_path.is_file():
                    return {
                        "success": False,
                        "error": f"Context file not found: {context_file}"
                    }
                    
                with context_path.open("r", encoding='utf-8') as f:
                    context_data = json.load(f)
                    prompt = self._generate_prompt_from_context(context_data)
                    
            # Ensure Cursor is running
            self._ensure_cursor_running()
            
            # Copy prompt to clipboard
            pyperclip.copy(prompt)
            
            # Give time for Cursor to be ready
            time.sleep(3)
            
            # Simulate paste
            pyautogui.hotkey('ctrl', 'v')
            
            return {
                "success": True,
                "data": {
                    "prompt_sent": True,
                    "prompt_length": len(prompt)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"UI interaction failed: {str(e)}"
            }
            
    def _generate_prompt_from_context(self, context: Dict) -> str:
        """Generate a natural language prompt from context data."""
        prompt = f"Context Analysis:\n"
        prompt += f"- Stall Category: {context.get('stall_category', 'Unknown')}\n"
        prompt += f"- Suggested Action: {context.get('suggested_action_keyword', 'N/A')}\n"
        prompt += f"- Project Root: {context.get('project_root', 'N/A')}\n"
        
        if context.get('relevant_files'):
            prompt += f"- Relevant Files: {', '.join(context['relevant_files'])}\n"
            
        if context.get('conversation_snippet'):
            prompt += f"\nConversation Snippet:\n```\n{context['conversation_snippet']}\n```\n"
            
        prompt += f"\nTask: Based on the stall category and context, please {context.get('suggested_action_keyword', 'diagnose the issue and propose a fix')}."
        return prompt
        
    def _ensure_cursor_running(self):
        """Ensure Cursor application is running."""
        try:
            subprocess.Popen([self.cursor_exe_path])
            time.sleep(7)  # Allow time for launch
        except Exception as e:
            self.logger.warning(f"Error launching Cursor (may already be running): {e}")
            
    def _get_default_cursor_path(self) -> str:
        """Get the default Cursor executable path based on OS."""
        if os.name == 'nt':  # Windows
            return r"C:\Users\User\AppData\Local\Programs\Cursor\Cursor.exe"
        else:  # macOS
            return "/Applications/Cursor.app/Contents/MacOS/Cursor" 