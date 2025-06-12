"""Test execution manager with feedback integration."""
import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
import pytest
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class TestExecutionManager:
    """Manages test execution and feedback integration."""
    
    def __init__(self, bot_root: str = "HCshinobi"):
        """Initialize the test execution manager."""
        self.bot_root = Path(bot_root)
        self.metrics_dir = self.bot_root / "data" / "metrics"
        self.feedback_file = self.bot_root / "data" / "feedback_memory.json"
        self.test_dir = self.bot_root / "tests"
        
        # Error pattern tracking
        self.error_patterns = {
            "timeout": re.compile(r"TimeoutError|asyncio\.TimeoutError"),
            "permission": re.compile(r"PermissionError|Forbidden"),
            "validation": re.compile(r"ValidationError|ValueError"),
            "network": re.compile(r"ConnectionError|NetworkError"),
            "database": re.compile(r"DatabaseError|IntegrityError"),
            "rate_limit": re.compile(r"RateLimit|TooManyRequests"),
            "unknown": re.compile(r".*")  # Catch-all pattern
        }
        
    def _load_feedback_memory(self) -> Dict:
        """Load feedback memory from JSON file."""
        try:
            if self.feedback_file.exists():
                with open(self.feedback_file, 'r') as f:
                    return json.load(f)
        except json.JSONDecodeError:
            logger.error("Failed to load feedback memory")
        return {}
        
    def _save_feedback_memory(self, feedback_data: Dict):
        """Save feedback memory to JSON file."""
        try:
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.feedback_file, 'w') as f:
                json.dump(feedback_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save feedback memory: {e}")
            
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message into known patterns."""
        for category, pattern in self.error_patterns.items():
            if pattern.search(error_message):
                return category
        return "unknown"
        
    def _update_error_patterns(self, error_message: str):
        """Update error patterns based on new errors."""
        # If error doesn't match any pattern, add it to the unknown pattern
        if not any(pattern.search(error_message) for pattern in self.error_patterns.values()):
            self.error_patterns["unknown"] = re.compile(
                f"{self.error_patterns['unknown'].pattern}|{re.escape(error_message)}"
            )
            
    async def execute_test_stub(self, test_file: Path) -> Dict:
        """Execute a test stub and return results."""
        try:
            # Run pytest asynchronously
            proc = await asyncio.create_subprocess_exec(
                "pytest",
                str(test_file),
                "--json-report",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            # Parse test results
            results = {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": [],
                "duration": 0.0
            }
            
            # Extract test results from stdout
            for line in stdout.decode().splitlines():
                if "FAILED" in line:
                    results["failed"] += 1
                    error_msg = line.split("FAILED")[1].strip()
                    results["errors"].append({
                        "message": error_msg,
                        "category": self._categorize_error(error_msg)
                    })
                elif "PASSED" in line:
                    results["passed"] += 1
                elif "SKIPPED" in line:
                    results["skipped"] += 1
                    
            return results
            
        except Exception as e:
            logger.error(f"Error executing test {test_file}: {e}")
            return {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "errors": [{
                    "message": str(e),
                    "category": "execution_error"
                }],
                "duration": 0.0
            }
            
    def update_feedback_memory(self, command_name: str, test_results: Dict):
        """Update feedback memory with test execution results."""
        feedback_data = self._load_feedback_memory()
        
        if command_name not in feedback_data:
            feedback_data[command_name] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "error_counts": {},
                "last_improvement": None,
                "test_results": []
            }
            
        # Update command metrics
        command_data = feedback_data[command_name]
        command_data["total_attempts"] += 1
        
        if test_results["failed"] == 0:
            command_data["successful_attempts"] += 1
            
        # Update error counts
        for error in test_results["errors"]:
            category = error["category"]
            if category not in command_data["error_counts"]:
                command_data["error_counts"][category] = 0
            command_data["error_counts"][category] += 1
            
        # Update test results history
        command_data["test_results"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "results": test_results
        })
        
        # Keep only last 10 test results
        command_data["test_results"] = command_data["test_results"][-10:]
        
        # Save updated feedback
        self._save_feedback_memory(feedback_data)
        
    async def process_test_queue(self, test_files: List[Path]):
        """Process a queue of test files and update feedback."""
        for test_file in test_files:
            logger.info(f"Executing test: {test_file}")
            
            # Extract command name from test file
            command_name = test_file.stem.replace("test_", "")
            
            # Execute test
            results = await self.execute_test_stub(test_file)
            
            # Update feedback memory
            self.update_feedback_memory(command_name, results)
            
            # Log results
            if results["failed"] > 0:
                logger.warning(
                    f"Test {test_file} failed: {results['failed']} failures, "
                    f"{results['passed']} passed"
                )
            else:
                logger.info(
                    f"Test {test_file} passed: {results['passed']} passed"
                )
                
    def get_command_priority_adjustment(self, command_name: str) -> float:
        """Calculate priority adjustment based on test results."""
        feedback_data = self._load_feedback_memory()
        command_data = feedback_data.get(command_name, {})
        
        if not command_data:
            return 0.0
            
        # Calculate success rate
        total_attempts = command_data["total_attempts"]
        successful_attempts = command_data["successful_attempts"]
        success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0
        
        # Calculate error impact
        error_impact = sum(
            count * (1.0 if category == "unknown" else 0.5)
            for category, count in command_data["error_counts"].items()
        )
        
        # Priority adjustment formula
        # Higher error impact and lower success rate = higher priority
        adjustment = (error_impact * 0.6) + ((1 - success_rate) * 0.4)
        
        return adjustment 