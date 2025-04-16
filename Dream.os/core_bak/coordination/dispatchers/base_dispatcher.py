"""Base class for all dispatchers in the system."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from queue import Queue

logger = logging.getLogger(__name__)

class BaseDispatcher(ABC):
    """Abstract base class for all dispatchers."""
    
    def __init__(self):
        self.task_queue = Queue()
        self.is_running = False
        self.current_task: Optional[Dict] = None
        
    @abstractmethod
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task and return the result.
        
        Args:
            task: Dictionary containing task details
                {
                    "id": str,
                    "type": str,
                    "payload": Dict[str, Any],
                    "metadata": Dict[str, Any]
                }
                
        Returns:
            Dict containing execution result and metadata
        """
        pass
        
    def run_dispatcher_loop(self):
        """Main loop that polls for tasks and executes them."""
        self.is_running = True
        logger.info(f"Starting {self.__class__.__name__} dispatcher loop")
        
        while self.is_running:
            try:
                # Process next task from queue
                if not self.task_queue.empty():
                    task = self.task_queue.get()
                    self.current_task = task
                    result = self.execute_task(task)
                    self._handle_task_result(task, result)
                    
            except Exception as e:
                logger.error(f"Error in dispatcher loop: {e}", exc_info=True)
                
    def stop(self):
        """Stop the dispatcher loop."""
        self.is_running = False
        logger.info(f"Stopping {self.__class__.__name__} dispatcher loop")
        
    def add_task(self, task: Dict[str, Any]):
        """Add a task to the queue."""
        self.task_queue.put(task)
        logger.info(f"Added task {task.get('id')} to {self.__class__.__name__} queue")
        
    def _handle_task_result(self, task: Dict[str, Any], result: Dict[str, Any]):
        """Handle the result of a task execution."""
        task_id = task.get('id', 'unknown')
        if result.get('success'):
            logger.info(f"Task {task_id} completed successfully")
        else:
            logger.error(f"Task {task_id} failed: {result.get('error')}")
            
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the dispatcher."""
        return {
            "is_running": self.is_running,
            "queue_size": self.task_queue.qsize(),
            "current_task": self.current_task
        } 