"""Command metrics logging service for HCshinobi."""
import json
import time
import logging
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class CommandLogger:
    """Service for logging and analyzing command usage metrics."""
    
    def __init__(self, metrics_dir: str = "data/metrics"):
        """Initialize the command logger."""
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics storage
        self.command_metrics = self._load_metrics()
        self.user_metrics = self._load_user_metrics()
        self.feedback_memory = self._load_feedback_memory()
        
        # Error pattern tracking
        self.error_patterns = {
            "permission_denied": r"(permission|access|denied|forbidden)",
            "invalid_input": r"(invalid|wrong|incorrect|missing)",
            "not_found": r"(not found|does not exist|no such)",
            "rate_limit": r"(rate limit|too many|slow down)",
            "timeout": r"(timeout|timed out|took too long)",
            "database": r"(database|connection|query|transaction)",
            "validation": r"(validation|required|constraint|check)"
        }
        
    def _load_metrics(self) -> Dict:
        """Load command metrics from file."""
        metrics_file = self.metrics_dir / "command_metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Failed to load command metrics, initializing empty")
        return {}
        
    def _load_user_metrics(self) -> Dict:
        """Load user metrics from file."""
        metrics_file = self.metrics_dir / "user_metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Failed to load user metrics, initializing empty")
        return {}
        
    def _load_feedback_memory(self) -> Dict:
        """Load feedback memory from file."""
        feedback_file = self.metrics_dir / "feedback_memory.json"
        if feedback_file.exists():
            try:
                with open(feedback_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Failed to load feedback memory, initializing empty")
        return {
            "error_patterns": {},
            "command_improvements": {},
            "user_feedback": {},
            "retry_success": {}
        }
        
    def _save_metrics(self):
        """Save command metrics to file."""
        metrics_file = self.metrics_dir / "command_metrics.json"
        try:
            with open(metrics_file, 'w') as f:
                json.dump(self.command_metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save command metrics: {e}")
            
    def _save_user_metrics(self):
        """Save user metrics to file."""
        metrics_file = self.metrics_dir / "user_metrics.json"
        try:
            with open(metrics_file, 'w') as f:
                json.dump(self.user_metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save user metrics: {e}")
            
    def _save_feedback_memory(self):
        """Save feedback memory to file."""
        feedback_file = self.metrics_dir / "feedback_memory.json"
        try:
            with open(feedback_file, 'w') as f:
                json.dump(self.feedback_memory, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save feedback memory: {e}")
            
    def _categorize_error(self, error: str) -> str:
        """Categorize an error message into a pattern."""
        for pattern_name, pattern in self.error_patterns.items():
            if re.search(pattern, error.lower()):
                return pattern_name
        return "unknown"
        
    def _update_error_patterns(self, error: str):
        """Update error pattern tracking in feedback memory."""
        pattern = self._categorize_error(error)
        if pattern not in self.feedback_memory["error_patterns"]:
            self.feedback_memory["error_patterns"][pattern] = 0
        self.feedback_memory["error_patterns"][pattern] += 1
        
    def _update_command_improvements(self, command_name: str, success: bool, error: Optional[str] = None):
        """Update command improvement tracking in feedback memory."""
        if command_name not in self.feedback_memory["command_improvements"]:
            self.feedback_memory["command_improvements"][command_name] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "error_patterns": {},
                "last_improvement": None
            }
            
        cmd_improvements = self.feedback_memory["command_improvements"][command_name]
        cmd_improvements["total_attempts"] += 1
        
        if success:
            cmd_improvements["successful_attempts"] += 1
            # Check if this is an improvement from previous failure
            if error and error in cmd_improvements["error_patterns"]:
                cmd_improvements["last_improvement"] = datetime.utcnow().isoformat()
        elif error:
            pattern = self._categorize_error(error)
            if pattern not in cmd_improvements["error_patterns"]:
                cmd_improvements["error_patterns"][pattern] = 0
            cmd_improvements["error_patterns"][pattern] += 1
            
    def log_command_usage(
        self,
        user_id: str,
        command_name: str,
        success: bool = True,
        duration_ms: float = 0,
        error: Optional[str] = None
    ):
        """
        Log command usage metrics and update feedback memory.
        
        Args:
            user_id: The ID of the user who invoked the command
            command_name: The name of the command
            success: Whether the command executed successfully
            duration_ms: How long the command took to execute
            error: Any error message if the command failed
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Update command metrics
        if command_name not in self.command_metrics:
            self.command_metrics[command_name] = {
                "total_uses": 0,
                "successful_uses": 0,
                "failed_uses": 0,
                "total_duration_ms": 0,
                "avg_duration_ms": 0,
                "last_used": None,
                "errors": {}
            }
            
        cmd_metrics = self.command_metrics[command_name]
        cmd_metrics["total_uses"] += 1
        cmd_metrics["total_duration_ms"] += duration_ms
        cmd_metrics["avg_duration_ms"] = cmd_metrics["total_duration_ms"] / cmd_metrics["total_uses"]
        cmd_metrics["last_used"] = timestamp
        
        if success:
            cmd_metrics["successful_uses"] += 1
        else:
            cmd_metrics["failed_uses"] += 1
            if error:
                if error not in cmd_metrics["errors"]:
                    cmd_metrics["errors"][error] = 0
                cmd_metrics["errors"][error] += 1
                
        # Update user metrics
        if user_id not in self.user_metrics:
            self.user_metrics[user_id] = {
                "total_commands": 0,
                "commands_used": {},
                "last_active": None
            }
            
        user_metrics = self.user_metrics[user_id]
        user_metrics["total_commands"] += 1
        user_metrics["last_active"] = timestamp
        
        if command_name not in user_metrics["commands_used"]:
            user_metrics["commands_used"][command_name] = 0
        user_metrics["commands_used"][command_name] += 1
        
        # Update feedback memory
        if error:
            self._update_error_patterns(error)
        self._update_command_improvements(command_name, success, error)
        
        # Save all data
        self._save_metrics()
        self._save_user_metrics()
        self._save_feedback_memory()
        
    def get_command_metrics(self, command_name: str) -> Optional[Dict]:
        """Get metrics for a specific command."""
        return self.command_metrics.get(command_name)
        
    def get_user_metrics(self, user_id: str) -> Optional[Dict]:
        """Get metrics for a specific user."""
        return self.user_metrics.get(user_id)
        
    def get_top_commands(self, limit: int = 10) -> List[Dict]:
        """Get the most used commands."""
        commands = []
        for name, metrics in self.command_metrics.items():
            commands.append({
                "name": name,
                "total_uses": metrics["total_uses"],
                "success_rate": metrics["successful_uses"] / metrics["total_uses"] if metrics["total_uses"] > 0 else 0,
                "avg_duration_ms": metrics["avg_duration_ms"]
            })
        return sorted(commands, key=lambda x: x["total_uses"], reverse=True)[:limit]
        
    def get_command_suggestions(self, user_id: str) -> List[str]:
        """Get command suggestions based on user's command history."""
        if user_id not in self.user_metrics:
            return []
            
        user_metrics = self.user_metrics[user_id]
        used_commands = set(user_metrics["commands_used"].keys())
        all_commands = set(self.command_metrics.keys())
        
        # Suggest commands the user hasn't used yet
        return list(all_commands - used_commands)
        
    def get_error_patterns(self) -> Dict[str, int]:
        """Get error pattern statistics."""
        return self.feedback_memory["error_patterns"]
        
    def get_command_improvements(self, command_name: str) -> Optional[Dict]:
        """Get improvement statistics for a command."""
        return self.feedback_memory["command_improvements"].get(command_name)
        
    def get_retry_success_rate(self, command_name: str) -> float:
        """Get the success rate of retried commands."""
        if command_name not in self.feedback_memory["command_improvements"]:
            return 0.0
            
        cmd_improvements = self.feedback_memory["command_improvements"][command_name]
        if cmd_improvements["total_attempts"] == 0:
            return 0.0
            
        return cmd_improvements["successful_attempts"] / cmd_improvements["total_attempts"] 