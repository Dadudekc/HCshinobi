"""
Thea Task Engine - Task Parser
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from . import task_engine

class TodoReportParser:
    def __init__(self, report_path: str):
        self.report_path = Path(report_path)
        self.workspace_root = self.report_path.parent
        self.categories = {
            'security': 'Security Concerns',
            'tests': 'Tests Needed',
            'performance': 'Performance Issues',
            'important': 'Important TODOs',
            'missing': 'Missing Implementations',
            'enhancement': 'Enhancement Ideas',
            'general': 'General TODOs'
        }
        
    def generate_tasks(self) -> None:
        """Generate tasks from the TODO report"""
        with open(self.report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract tasks from each category
        for category_id, category_name in self.categories.items():
            tasks = self._extract_tasks_for_category(category_id, category_name, content)
            for task_data in tasks:
                task = {
                    'category': category_id,
                    'type': 'todo',
                    'priority': self._calculate_priority(category_id, task_data),
                    'target_files': [task_data['file']],
                    'description': task_data['description'],
                    'line_number': task_data.get('line_number'),
                    'status': 'pending'
                }
                task_engine.add_task(task)
                
    def _extract_tasks_for_category(self, category_id: str, category_name: str, content: str) -> List[Dict[str, Any]]:
        """Extract tasks for a specific category"""
        tasks = []
        category_pattern = rf"### {category_name}\n(.*?)(?=###|\Z)"
        category_match = re.search(category_pattern, content, re.DOTALL)
        
        if category_match:
            category_content = category_match.group(1)
            task_pattern = r"\- \[([ x])\] (.*?) \(([^)]+)\)"
            
            for match in re.finditer(task_pattern, category_content):
                status, description, file_info = match.groups()
                file_path, line_number = self._parse_file_info(file_info)
                
                tasks.append({
                    'file': file_path,
                    'line_number': line_number,
                    'description': description,
                    'is_completed': status == 'x'
                })
                
        return tasks
        
    def _parse_file_info(self, file_info: str) -> Tuple[str, Optional[int]]:
        """Parse file path and line number from file info string"""
        parts = file_info.split(':')
        file_path = parts[0]
        line_number = int(parts[1]) if len(parts) > 1 else None
        return file_path, line_number
        
    def _calculate_priority(self, category: str, task_data: Dict[str, Any]) -> int:
        """Calculate task priority based on category and content"""
        base_priority = {
            'security': 100,
            'tests': 80,
            'performance': 70,
            'important': 60,
            'missing': 50,
            'enhancement': 30,
            'general': 20
        }.get(category, 0)
        
        # Adjust priority based on description keywords
        description = task_data['description'].lower()
        if any(kw in description for kw in ['critical', 'urgent', 'high priority']):
            base_priority += 20
        elif any(kw in description for kw in ['important', 'needed', 'required']):
            base_priority += 10
            
        return base_priority 