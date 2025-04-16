from typing import Dict, Any
from datetime import datetime

class FeedbackEngine:
    """
    Processes and routes feedback from task executions.
    Integrates with memory systems and prompt refinement.
    """
    
    def __init__(self):
        self.feedback_history = {}
        self.retry_counts = {}
        self.max_retries = 3
    
    def process_feedback(self, task_id: str, agent_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        Process feedback from task execution and route appropriately.
        
        Args:
            task_id: Unique identifier for the task
            agent_id: ID of the agent providing feedback
            feedback_data: Execution feedback and metrics
            
        Returns:
            bool: True if feedback was processed successfully
        """
        try:
            # Record feedback with timestamp
            if task_id not in self.feedback_history:
                self.feedback_history[task_id] = []
            
            self.feedback_history[task_id].append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": agent_id,
                "feedback": feedback_data
            })
            
            # Track retry counts
            if not feedback_data.get("success", False):
                self.retry_counts[task_id] = self.retry_counts.get(task_id, 0) + 1
            
            return True
            
        except Exception as e:
            print(f"Error processing feedback for task {task_id}: {e}")
            return False
    
    def get_retry_count(self, task_id: str) -> int:
        """Get the number of retries for a task."""
        return self.retry_counts.get(task_id, 0)
    
    def should_retry(self, task_id: str) -> bool:
        """Determine if a task should be retried based on history."""
        return self.get_retry_count(task_id) < self.max_retries
    
    def get_task_history(self, task_id: str) -> list:
        """Get the feedback history for a task."""
        return self.feedback_history.get(task_id, []) 