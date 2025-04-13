"""
Thea Task Engine - Core Task Management
"""

from typing import Dict, List, Any
from pathlib import Path
from .parser import TodoReportParser

class TheaTaskEngine:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_counter = 0
        self.parser = None
        
    def add_task(self, task: Dict[str, Any]) -> str:
        """Add a task to the engine"""
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1
        self.tasks[task_id] = task
        return task_id
        
    def get_tasks_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all tasks for a specific category"""
        return [task for task in self.tasks.values() 
                if task.get('category', '').startswith(category)]
                
    def mark_task_completed(self, task: Dict[str, Any]) -> None:
        """Mark a task as completed"""
        task_id = next((tid for tid, t in self.tasks.items() if t == task), None)
        if task_id:
            self.tasks[task_id]['status'] = 'completed'
            
    def parse_tasks(self, report_path: str) -> None:
        """Parse tasks from the TODO report"""
        self.parser = TodoReportParser(report_path)
        self.parser.generate_tasks()

# Global task engine instance
task_engine = TheaTaskEngine() 