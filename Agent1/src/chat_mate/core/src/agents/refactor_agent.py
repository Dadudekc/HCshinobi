from typing import Dict, Any
from core.Agents.CursorAgentInterface import CursorAgentInterface
import aiohttp

class RefactorAgent(CursorAgentInterface):
    """Agent for handling code refactoring tasks."""
    
    def run_task(self, prompt_template: str, target_file: str) -> Dict[str, Any]:
        """Run a refactoring task."""
        self._log_task_start("Refactor", target_file)
        
        # Format the prompt
        prompt = self._format_prompt(prompt_template, file=target_file)
        
        # Log the prompt for manual execution
        self.logger.log_debug(f"Refactor prompt for {target_file}:\n{prompt}")
        
        # TODO: When Cursor API is available, automate this
        print("\n=== Cursor Refactor Prompt ===\n")
        print(prompt)
        print("\n=== End Prompt ===\n")
        
        # Return pseudo-result
        result = {
            "status": "completed",
            "file": target_file,
            "prompt": prompt,
            "metrics": {
                "complexity_reduction": 0.0,  # To be calculated
                "test_coverage": 0.0,  # To be calculated
                "maintainability_score": 0.0  # To be calculated
            }
        }
        
        self._log_task_complete("Refactor", target_file, result)
        return result
        
    def run_refactor(self, target_file: str) -> Dict[str, Any]:
        """Run a standard refactoring task."""
        prompt_template = """
TASK: Refactor the following module for better scalability, readability, and maintainability.
MODE: FULL SYNC MODE

CONSTRAINTS:
- Follow SOLID and DRY principles
- Add type hints
- Simplify complex functions
- Maintain test coverage
- Provide a git commit message after completion

INPUT FILE:
{file}

OUTPUT:
1. Refactored code with improved structure
2. Updated type hints
3. Simplified complex functions
4. Git commit message
"""
        return self.run_task(prompt_template, target_file)

    async def refactor_file(self, target_file: str, prompt: str) -> Dict[str, Any]:
        """
        Refactor a file using the Cursor API.
        
        Args:
            target_file: Path to the file to refactor
            prompt: Refactoring instructions
            
        Returns:
            Dictionary containing refactoring results
        """
        try:
            # Log the refactoring request
            self.logger.log_debug(f"Refactoring {target_file} with prompt:\n{prompt}")
            
            # Prepare API request
            api_request = {
                "action": "refactor",
                "file_path": target_file,
                "prompt": prompt,
                "options": {
                    "preserve_comments": True,
                    "maintain_formatting": True,
                    "update_imports": True
                }
            }
            
            # Call Cursor API
            response = await self._call_cursor_api(api_request)
            
            if response.get("success"):
                self.logger.log_info(f"Successfully refactored {target_file}")
                return {
                    "status": "success",
                    "changes": response.get("changes", []),
                    "warnings": response.get("warnings", [])
                }
            else:
                error_msg = response.get("error", "Unknown error")
                self.logger.log_error(f"Failed to refactor {target_file}: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg
                }
                
        except Exception as e:
            self.logger.log_error(f"Error during refactoring: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    async def _call_cursor_api(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the Cursor API with the given request.
        
        Args:
            request: API request parameters
            
        Returns:
            API response
        """
        try:
            # TODO: Replace with actual API endpoint
            api_url = "https://api.cursor.sh/v1/refactor"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=request) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {
                            "success": False,
                            "error": f"API request failed with status {response.status}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "error": f"API call failed: {str(e)}"
            } 
