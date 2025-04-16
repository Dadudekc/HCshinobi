"""Unified prompt dispatcher that handles both file-based and direct prompts."""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pyperclip
import pyautogui

from .base_dispatcher import BaseDispatcher

class PromptDispatcher(BaseDispatcher):
    """
    Handles dispatching of prompts to various targets (UI, files, etc).
    """
    
    def __init__(self, prompt_library_dir: Optional[str] = None):
        super().__init__()
        self.prompt_library_dir = Path(prompt_library_dir) if prompt_library_dir else self._get_default_library_dir()
        self.prompt_library_dir.mkdir(parents=True, exist_ok=True)
        
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a prompt dispatch task."""
        try:
            task_type = task.get("type", "direct")
            payload = task.get("payload", {})
            
            if task_type == "file":
                return self._handle_file_prompt(payload)
            elif task_type == "direct":
                return self._handle_direct_prompt(payload)
            else:
                return {"success": False, "error": f"Unsupported task type: {task_type}"}
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metadata": {"exception_type": type(e).__name__}
            }
            
    def _handle_file_prompt(self, payload: Dict) -> Dict:
        """Handle prompts stored in files."""
        prompt_name = payload.get("prompt_name")
        if not prompt_name:
            return {
                "success": False,
                "error": "Missing required field: prompt_name"
            }
            
        try:
            prompt_file = self.prompt_library_dir / f"{prompt_name}.txt"
            if not prompt_file.is_file():
                return {
                    "success": False,
                    "error": f"Prompt file not found: {prompt_file}"
                }
                
            prompt_text = prompt_file.read_text(encoding='utf-8').strip()
            if not prompt_text:
                return {
                    "success": False,
                    "error": f"Prompt file is empty: {prompt_file}"
                }
                
            return self._dispatch_prompt(prompt_text, payload)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"File prompt handling failed: {str(e)}"
            }
            
    def _handle_direct_prompt(self, payload: Dict) -> Dict:
        """Handle direct prompt text."""
        prompt = payload.get("prompt")
        if not prompt:
            return {
                "success": False,
                "error": "Missing required field: prompt"
            }
            
        return self._dispatch_prompt(prompt, payload)
        
    def _dispatch_prompt(self, prompt_text: str, options: Dict) -> Dict:
        """Common prompt dispatch logic."""
        try:
            # Copy to clipboard
            pyperclip.copy(prompt_text)
            
            # Wait for target window focus if specified
            focus_delay = options.get("focus_delay", 3)
            if focus_delay > 0:
                time.sleep(focus_delay)
                
            # Simulate paste
            if options.get("use_paste", True):
                pyautogui.hotkey('ctrl', 'v')
                
            # Optional auto-send
            if options.get("auto_send"):
                time.sleep(0.5)
                pyautogui.press('enter')
                
            return {
                "success": True,
                "data": {
                    "prompt_length": len(prompt_text),
                    "auto_sent": options.get("auto_send", False)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Prompt dispatch failed: {str(e)}"
            }
            
    def list_available_prompts(self) -> Dict[str, Any]:
        """List all available prompts in the library."""
        try:
            prompts = [f.stem for f in self.prompt_library_dir.iterdir() 
                      if f.is_file() and f.suffix == '.txt']
            return {
                "success": True,
                "data": {
                    "prompts": sorted(prompts),
                    "count": len(prompts)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list prompts: {str(e)}"
            }
            
    def _get_default_library_dir(self) -> Path:
        """Get the default prompt library directory."""
        return Path(os.path.expanduser("~")) / ".dreamforge" / "prompts" 