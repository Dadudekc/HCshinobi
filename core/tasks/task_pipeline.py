"""Task pipeline manager for HCshinobi."""
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import asyncio
from core.coverage.test_coverage_analyzer import TestCoverageAnalyzer

logger = logging.getLogger(__name__)

class TaskPipeline:
    """Manages task execution pipeline."""
    
    def __init__(self, bot_root: str = "HCshinobi"):
        """Initialize the task pipeline."""
        self.bot_root = Path(bot_root)
        self.tasks_dir = self.bot_root / "data" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize analyzers
        self.coverage_analyzer = TestCoverageAnalyzer(bot_root)
        
    def _load_task_queue(self, queue_file: str = "test_generation_queue.json") -> List[Dict]:
        """Load task queue from file."""
        queue_path = self.tasks_dir / queue_file
        if queue_path.exists():
            try:
                with open(queue_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Failed to load task queue from {queue_path}")
        return []
        
    def _save_task_queue(self, tasks: List[Dict], queue_file: str = "test_generation_queue.json"):
        """Save task queue to file."""
        queue_path = self.tasks_dir / queue_file
        try:
            with open(queue_path, 'w') as f:
                json.dump(tasks, f, indent=2)
            logger.info(f"Saved task queue to {queue_path}")
        except Exception as e:
            logger.error(f"Failed to save task queue: {e}")
            
    def _update_task_status(self, task: Dict, status: str, error: Optional[str] = None):
        """Update task status in queue."""
        task["status"] = status
        task["updated_at"] = datetime.utcnow().isoformat()
        if error:
            task["error"] = error
            
    async def process_test_generation_task(self, task: Dict) -> Dict:
        """Process a test generation task."""
        try:
            # Generate test file
            file_path = self.bot_root / task["target_file"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(task["stub"])
                
            self._update_task_status(task, "completed")
            logger.info(f"Generated test file for {task['command']}")
            
        except Exception as e:
            error_msg = f"Failed to generate test for {task['command']}: {str(e)}"
            self._update_task_status(task, "failed", error_msg)
            logger.error(error_msg)
            
        return task
        
    async def process_task_queue(self, queue_file: str = "test_generation_queue.json"):
        """Process all tasks in the queue."""
        tasks = self._load_task_queue(queue_file)
        if not tasks:
            logger.info("No tasks in queue")
            return
            
        # Process tasks in priority order
        for task in tasks:
            if task.get("status") in ["completed", "failed"]:
                continue
                
            self._update_task_status(task, "processing")
            await self.process_test_generation_task(task)
            
        # Save updated queue
        self._save_task_queue(tasks, queue_file)
        
    def get_task_status(self, queue_file: str = "test_generation_queue.json") -> Dict:
        """Get status of all tasks in queue."""
        tasks = self._load_task_queue(queue_file)
        
        status_counts = {
            "total": len(tasks),
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        
        for task in tasks:
            status = task.get("status", "pending")
            status_counts[status] += 1
            
        return status_counts
        
    def get_next_task(self, queue_file: str = "test_generation_queue.json") -> Optional[Dict]:
        """Get the next pending task from the queue."""
        tasks = self._load_task_queue(queue_file)
        
        # Find highest priority pending task
        pending_tasks = [t for t in tasks if t.get("status") == "pending"]
        if not pending_tasks:
            return None
            
        return min(pending_tasks, key=lambda x: x["priority"])
        
    async def run_pipeline(self):
        """Run the task pipeline."""
        while True:
            try:
                # Check for new tasks
                next_task = self.get_next_task()
                if next_task:
                    await self.process_task_queue()
                    
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in task pipeline: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error 