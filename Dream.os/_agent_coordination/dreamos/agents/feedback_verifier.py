"""FeedbackVerifierAgent - Validates changes and provides execution feedback."""

import logging
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
import json
from datetime import datetime

from dreamos.agents import ExecutionResult, TaskMetadata

logger = logging.getLogger(__name__)

class FeedbackVerifierAgent:
    """Agent responsible for validating changes and providing feedback."""
    
    def __init__(self, workspace_dir: str, feedback_dir: str = "queue/feedback"):
        """Initialize the FeedbackVerifierAgent.
        
        Args:
            workspace_dir: Directory containing the workspace files
            feedback_dir: Directory for storing feedback and validation results
        """
        self.workspace_dir = Path(workspace_dir)
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
    async def verify_changes(self, result: ExecutionResult, task: TaskMetadata) -> Dict:
        """Verify changes made by an execution.
        
        Args:
            result: ExecutionResult object to verify
            task: TaskMetadata object containing success criteria
            
        Returns:
            Verification results dictionary
        """
        verification = {
            "prompt_id": result.prompt_id,
            "task_id": task.task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": True,
            "checks": []
        }
        
        # Run syntax check
        syntax_check = self._check_syntax(task.target_files)
        verification["checks"].append({
            "type": "syntax",
            "success": syntax_check["success"],
            "details": syntax_check
        })
        
        # Run linter
        lint_check = self._run_linter(task.target_files)
        verification["checks"].append({
            "type": "linting",
            "success": lint_check["success"],
            "details": lint_check
        })
        
        # Run tests if applicable
        test_results = self._run_tests(task.target_files)
        verification["checks"].append({
            "type": "tests",
            "success": test_results["success"],
            "details": test_results
        })
        
        # Check success criteria
        criteria_check = self._check_success_criteria(task.success_criteria)
        verification["checks"].append({
            "type": "success_criteria",
            "success": criteria_check["success"],
            "details": criteria_check
        })
        
        # Overall success requires all checks to pass
        verification["success"] = all(
            check["success"] for check in verification["checks"]
        )
        
        self._save_verification(verification)
        return verification
    
    def _check_syntax(self, files: List[str]) -> Dict:
        """Check Python syntax in modified files.
        
        Args:
            files: List of files to check
            
        Returns:
            Syntax check results
        """
        results = {
            "success": True,
            "errors": []
        }
        
        for file_path in files:
            if not file_path.endswith('.py'):
                continue
                
            try:
                full_path = self.workspace_dir / file_path
                with open(full_path, 'r') as f:
                    compile(f.read(), file_path, 'exec')
            except SyntaxError as e:
                results["success"] = False
                results["errors"].append({
                    "file": file_path,
                    "line": e.lineno,
                    "message": str(e)
                })
                
        return results
    
    def _run_linter(self, files: List[str]) -> Dict:
        """Run pylint on modified files.
        
        Args:
            files: List of files to lint
            
        Returns:
            Linting results
        """
        results = {
            "success": True,
            "errors": [],
            "warnings": []
        }
        
        for file_path in files:
            if not file_path.endswith('.py'):
                continue
                
            try:
                full_path = self.workspace_dir / file_path
                process = subprocess.run(
                    ['pylint', str(full_path)],
                    capture_output=True,
                    text=True
                )
                
                if process.returncode != 0:
                    results["success"] = False
                    for line in process.stdout.splitlines():
                        if 'error' in line.lower():
                            results["errors"].append({
                                "file": file_path,
                                "message": line
                            })
                        elif 'warning' in line.lower():
                            results["warnings"].append({
                                "file": file_path,
                                "message": line
                            })
            except Exception as e:
                logger.error(f"Linting failed for {file_path}: {e}")
                results["success"] = False
                results["errors"].append({
                    "file": file_path,
                    "message": f"Linting failed: {str(e)}"
                })
                
        return results
    
    def _run_tests(self, files: List[str]) -> Dict:
        """Run pytest for modified files.
        
        Args:
            files: List of modified files
            
        Returns:
            Test execution results
        """
        results = {
            "success": True,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # Find corresponding test files
            test_files = []
            for file_path in files:
                if file_path.endswith('.py'):
                    test_file = self.workspace_dir / 'tests' / f'test_{Path(file_path).name}'
                    if test_file.exists():
                        test_files.append(str(test_file))
            
            if not test_files:
                results["success"] = True
                return results
                
            # Run pytest
            process = subprocess.run(
                ['pytest', '-v'] + test_files,
                capture_output=True,
                text=True
            )
            
            # Parse pytest output
            for line in process.stdout.splitlines():
                if 'collected' in line:
                    results["total"] = int(line.split()[1])
                elif 'passed' in line:
                    results["passed"] += 1
                elif 'failed' in line:
                    results["failed"] += 1
                    results["success"] = False
                elif 'FAILED' in line:
                    results["errors"].append(line)
                    
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))
            
        return results
    
    def _check_success_criteria(self, criteria: Dict) -> Dict:
        """Check if changes meet success criteria.
        
        Args:
            criteria: Dict of success criteria to check
            
        Returns:
            Criteria check results
        """
        results = {
            "success": True,
            "met_criteria": [],
            "failed_criteria": []
        }
        
        for criterion, value in criteria.items():
            # TODO: Implement actual criteria checking logic
            # This is a placeholder that assumes all criteria are met
            results["met_criteria"].append({
                "criterion": criterion,
                "value": value,
                "actual": value
            })
            
        results["success"] = len(results["failed_criteria"]) == 0
        return results
    
    def _save_verification(self, verification: Dict) -> None:
        """Save verification results to file.
        
        Args:
            verification: Verification results to save
        """
        feedback_file = self.feedback_dir / f"verify_{verification['prompt_id']}.json"
        try:
            with open(feedback_file, 'w') as f:
                json.dump(verification, f, indent=2)
            logger.info(f"Saved verification results for prompt {verification['prompt_id']}")
        except Exception as e:
            logger.error(f"Failed to save verification results: {e}")
    
    def get_verification(self, prompt_id: str) -> Optional[Dict]:
        """Load verification results for a prompt.
        
        Args:
            prompt_id: ID of the prompt
            
        Returns:
            Verification results if found, None otherwise
        """
        feedback_file = self.feedback_dir / f"verify_{prompt_id}.json"
        if not feedback_file.exists():
            return None
            
        try:
            with open(feedback_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load verification results: {e}")
            return None
    
    def generate_summary(self, task_id: str, results: List[ExecutionResult]) -> Dict:
        """Generate summary of all verifications for a task.
        
        Args:
            task_id: ID of the task
            results: List of ExecutionResult objects
            
        Returns:
            Summary dictionary
        """
        summary = {
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "total_prompts": len(results),
            "successful_prompts": 0,
            "failed_prompts": 0,
            "total_changes": 0,
            "errors": [],
            "warnings": []
        }
        
        for result in results:
            verification = self.get_verification(result.prompt_id)
            if not verification:
                continue
                
            if verification["success"]:
                summary["successful_prompts"] += 1
            else:
                summary["failed_prompts"] += 1
                
            for check in verification["checks"]:
                if check["type"] == "linting":
                    summary["errors"].extend(check["details"]["errors"])
                    summary["warnings"].extend(check["details"]["warnings"])
                    
        return summary 