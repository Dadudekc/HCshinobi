from typing import Dict, Any
from core.Agents.CursorAgentInterface import CursorAgentInterface
import aiohttp

class TestAgent(CursorAgentInterface):
    """Agent for handling test generation tasks."""
    
    def run_task(self, prompt_template: str, target_file: str) -> Dict[str, Any]:
        """Run a test generation task."""
        self._log_task_start("TestGeneration", target_file)
        
        # Format the prompt
        prompt = self._format_prompt(prompt_template, file=target_file)
        
        # Log the prompt for manual execution
        self.logger.log_debug(f"Test generation prompt for {target_file}:\n{prompt}")
        
        # TODO: When Cursor API is available, automate this
        print("\n=== Cursor Test Generation Prompt ===\n")
        print(prompt)
        print("\n=== End Prompt ===\n")
        
        # Return pseudo-result
        result = {
            "status": "completed",
            "file": target_file,
            "prompt": prompt,
            "metrics": {
                "test_coverage": 0.0,  # To be calculated
                "edge_cases_covered": 0,  # To be calculated
                "test_count": 0  # To be calculated
            }
        }
        
        self._log_task_complete("TestGeneration", target_file, result)
        return result
        
    def run_tests(self, target_file: str) -> Dict[str, Any]:
        """Run a standard test generation task."""
        prompt_template = """
TASK: Generate comprehensive unit tests for the following module.
MODE: TDD MODE

CONSTRAINTS:
- Cover edge cases and failure scenarios
- Mock external dependencies
- Ensure test isolation (no side effects)
- Maintain 90%+ coverage
- Output tests in tests/test_{module}.py

INPUT FILE:
{file}

OUTPUT:
1. Unit tests with edge cases
2. Mocked dependencies
3. Test coverage report
4. Git commit message
"""
        return self.run_task(prompt_template, target_file)

    async def generate_tests(self, target_file: str, prompt: str) -> Dict[str, Any]:
        """
        Generate tests for a file using the Cursor API.
        
        Args:
            target_file: Path to the file to generate tests for
            prompt: Test generation instructions
            
        Returns:
            Dictionary containing test generation results
        """
        try:
            # Log the test generation request
            self.logger.log_debug(f"Generating tests for {target_file} with prompt:\n{prompt}")
            
            # Prepare API request
            api_request = {
                "action": "generate_tests",
                "file_path": target_file,
                "prompt": prompt,
                "options": {
                    "test_framework": "pytest",
                    "coverage_target": 0.8,
                    "include_docstrings": True
                }
            }
            
            # Call Cursor API
            response = await self._call_cursor_api(api_request)
            
            if response.get("success"):
                self.logger.log_info(f"Successfully generated tests for {target_file}")
                return {
                    "status": "success",
                    "test_file": response.get("test_file"),
                    "coverage": response.get("coverage"),
                    "warnings": response.get("warnings", [])
                }
            else:
                error_msg = response.get("error", "Unknown error")
                self.logger.log_error(f"Failed to generate tests for {target_file}: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg
                }
                
        except Exception as e:
            self.logger.log_error(f"Error during test generation: {str(e)}")
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
            api_url = "https://api.cursor.sh/v1/tests"
            
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
