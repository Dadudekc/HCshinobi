"""
Thea Task Engine - Preview Module
"""

from typing import Dict, List
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from . import task_engine
from .orchestrator import TheaOrchestrator

class TaskPreview:
    def __init__(self, orchestrator: TheaOrchestrator):
        self.orchestrator = orchestrator
        self.console = Console()
        
    def generate_preview(self):
        """Generate a comprehensive preview of all tasks and campaigns"""
        self.console.print(Panel.fit("🎯 Thea Task Engine - Preview Mode", style="bold blue"))
        
        # Show campaign overview
        self._show_campaign_overview()
        
        # Show task distribution
        self._show_task_distribution()
        
        # Show high-priority tasks
        self._show_high_priority_tasks()
        
        # Show file impact analysis
        self._show_file_impact()
        
    def _show_campaign_overview(self):
        """Display campaign status and schedule"""
        table = Table(title="Campaign Overview", show_header=True, header_style="bold magenta")
        table.add_column("Campaign", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Frequency", style="yellow")
        table.add_column("Next Run", style="blue")
        
        status = self.orchestrator.get_status()
        for campaign_id, info in status.items():
            table.add_row(
                info["name"],
                info["agent"],
                str(self.orchestrator.campaigns[campaign_id]["frequency"]),
                str(info["next_run"])
            )
            
        self.console.print(table)
        
    def _show_task_distribution(self):
        """Show distribution of tasks across categories"""
        table = Table(title="Task Distribution", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("High Priority", style="red")
        table.add_column("Medium Priority", style="yellow")
        table.add_column("Low Priority", style="blue")
        
        categories = {}
        for task in task_engine.tasks.values():
            category = task.get('category', 'unknown')
            if category not in categories:
                categories[category] = {"total": 0, "high": 0, "medium": 0, "low": 0}
            categories[category]["total"] += 1
            priority = task.get('priority', 0)
            if priority >= 80:
                categories[category]["high"] += 1
            elif priority >= 50:
                categories[category]["medium"] += 1
            else:
                categories[category]["low"] += 1
                
        for category, stats in categories.items():
            table.add_row(
                category,
                str(stats["total"]),
                str(stats["high"]),
                str(stats["medium"]),
                str(stats["low"])
            )
            
        self.console.print(table)
        
    def _show_high_priority_tasks(self):
        """Display high-priority tasks that will be addressed first"""
        high_priority_tasks = sorted(
            [t for t in task_engine.tasks.values() if t.get('priority', 0) >= 80],
            key=lambda x: x.get('priority', 0),
            reverse=True
        )[:10]  # Show top 10
        
        if high_priority_tasks:
            table = Table(title="Top 10 High-Priority Tasks", show_header=True, header_style="bold magenta")
            table.add_column("Priority", style="red")
            table.add_column("Category", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Description", style="yellow")
            
            for task in high_priority_tasks:
                table.add_row(
                    str(task.get('priority', 0)),
                    task.get('category', 'unknown'),
                    task.get('type', 'unknown'),
                    task.get('description', 'No description')[:100] + "..." if len(task.get('description', '')) > 100 else task.get('description', 'No description')
                )
                
            self.console.print(table)
            
    def _show_file_impact(self):
        """Show which files will be most affected"""
        file_impact = {}
        for task in task_engine.tasks.values():
            for file in task.get('target_files', []):
                if file not in file_impact:
                    file_impact[file] = {'count': 0, 'metrics': {}}
                file_impact[file]['count'] += 1
                if 'metrics' in task:
                    file_impact[file]['metrics'] = task['metrics']
                
        sorted_files = sorted(file_impact.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
        
        if sorted_files:
            table = Table(title="Top 10 Most Impacted Files", show_header=True, header_style="bold magenta")
            table.add_column("File", style="cyan")
            table.add_column("Task Count", style="green")
            table.add_column("Size", style="yellow")
            table.add_column("Lines", style="blue")
            
            for file, info in sorted_files:
                metrics = info['metrics']
                table.add_row(
                    str(file),
                    str(info['count']),
                    f"{metrics.get('file_size', 0) / 1024:.1f}KB" if metrics else "N/A",
                    str(metrics.get('line_count', 'N/A')) if metrics else "N/A"
                )
                
            self.console.print(table)

def generate_preview(report_path: str):
    """Generate a preview of the cleanup operation"""
    orchestrator = TheaOrchestrator(report_path)
    orchestrator.initialize()  # Parse tasks but don't execute
    
    preview = TaskPreview(orchestrator)
    preview.generate_preview() 