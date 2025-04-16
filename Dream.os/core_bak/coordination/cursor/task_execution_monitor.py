"""Real-time visual monitor for task execution feedback."""

import sys
import json
from datetime import datetime
from typing import Dict, Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QScrollArea, QFrame, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QPalette

class TaskStepWidget(QFrame):
    """Widget displaying a single task step's status."""
    
    def __init__(self, step_data: Dict, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header with action type and element
        header = QHBoxLayout()
        action_label = QLabel(f"Action: {step_data['action']}")
        action_label.setStyleSheet("font-weight: bold;")
        header.addWidget(action_label)
        if step_data.get('element'):
            element_label = QLabel(f"Element: {step_data['element']}")
            element_label.setStyleSheet("color: #666;")
            header.addWidget(element_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Progress and status
        status_layout = QHBoxLayout()
        self.status_label = QLabel(step_data['state'])
        self.status_label.setStyleSheet(self._get_state_style(step_data['state']))
        status_layout.addWidget(self.status_label)
        
        if step_data.get('result'):
            result = step_data['result']
            if result.get('success'):
                duration = result.get('duration', 0)
                status_layout.addWidget(QLabel(f"Duration: {duration:.2f}s"))
            else:
                error_label = QLabel(f"Error: {result.get('message', 'Unknown error')}")
                error_label.setStyleSheet("color: red;")
                status_layout.addWidget(error_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Timing info
        if step_data.get('started_at'):
            timing = QHBoxLayout()
            started = datetime.fromisoformat(step_data['started_at'])
            timing.addWidget(QLabel(f"Started: {started.strftime('%H:%M:%S')}"))
            
            if step_data.get('completed_at'):
                completed = datetime.fromisoformat(step_data['completed_at'])
                timing.addWidget(QLabel(f"Completed: {completed.strftime('%H:%M:%S')}"))
            
            timing.addStretch()
            layout.addLayout(timing)
    
    def _get_state_style(self, state: str) -> str:
        """Get CSS style for state label."""
        colors = {
            'pending': '#666',
            'running': '#007bff',
            'retrying': '#ffc107',
            'completed': '#28a745',
            'failed': '#dc3545',
            'skipped': '#6c757d'
        }
        return f"color: {colors.get(state.lower(), '#000')}; font-weight: bold;"

class TaskWidget(QFrame):
    """Widget displaying a complete task's execution status."""
    
    def __init__(self, task_data: Dict, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Task header
        header = QHBoxLayout()
        task_id = QLabel(f"Task: {task_data['task_id']}")
        task_id.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(task_id)
        
        state = QLabel(task_data['state'])
        state.setStyleSheet(self._get_state_style(task_data['state']))
        header.addWidget(state)
        
        if task_data.get('cursor_instance_id'):
            instance = QLabel(f"Instance: {task_data['cursor_instance_id']}")
            instance.setStyleSheet("color: #666;")
            header.addWidget(instance)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Progress bar
        self.progress = QProgressBar()
        total_steps = len(task_data['steps'])
        completed_steps = sum(1 for s in task_data['steps'] 
                            if s['state'] in ['completed', 'skipped'])
        self.progress.setMaximum(total_steps)
        self.progress.setValue(completed_steps)
        layout.addWidget(self.progress)
        
        # Steps
        steps_widget = QWidget()
        steps_layout = QVBoxLayout()
        steps_widget.setLayout(steps_layout)
        
        for step in task_data['steps']:
            step_widget = TaskStepWidget(step)
            steps_layout.addWidget(step_widget)
        
        steps_scroll = QScrollArea()
        steps_scroll.setWidget(steps_widget)
        steps_scroll.setWidgetResizable(True)
        layout.addWidget(steps_scroll)
        
        # Error message if any
        if task_data.get('error_message'):
            error = QLabel(f"Error: {task_data['error_message']}")
            error.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(error)
    
    def _get_state_style(self, state: str) -> str:
        """Get CSS style for state label."""
        colors = {
            'pending': '#666',
            'preparing': '#17a2b8',
            'running': '#007bff',
            'paused': '#ffc107',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d'
        }
        return f"color: {colors.get(state.lower(), '#000')}; font-weight: bold;"

class TaskMonitorSignals(QObject):
    """Signals for task monitor updates."""
    task_updated = pyqtSignal(str, dict)  # task_id, task_data

class TaskExecutionMonitor(QMainWindow):
    """Main window for monitoring task execution."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cursor Task Execution Monitor")
        self.resize(800, 600)
        
        # Central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)
        
        # Header with stats
        self.stats_layout = QHBoxLayout()
        self.active_tasks = QLabel("Active Tasks: 0")
        self.completed_tasks = QLabel("Completed: 0")
        self.failed_tasks = QLabel("Failed: 0")
        
        for label in [self.active_tasks, self.completed_tasks, self.failed_tasks]:
            label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 5px;")
            self.stats_layout.addWidget(label)
        
        self.stats_layout.addStretch()
        layout.addLayout(self.stats_layout)
        
        # Task container
        tasks_widget = QWidget()
        self.tasks_layout = QVBoxLayout()
        tasks_widget.setLayout(self.tasks_layout)
        
        tasks_scroll = QScrollArea()
        tasks_scroll.setWidget(tasks_widget)
        tasks_scroll.setWidgetResizable(True)
        layout.addWidget(tasks_scroll)
        
        # Setup signals and state
        self.signals = TaskMonitorSignals()
        self.signals.task_updated.connect(self._update_task)
        self.task_widgets: Dict[str, TaskWidget] = {}
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_stats)
        self.update_timer.start(1000)  # Update every second
    
    def _update_task(self, task_id: str, task_data: Dict):
        """Update or create task widget."""
        if task_id in self.task_widgets:
            # Remove existing widget
            old_widget = self.task_widgets[task_id]
            self.tasks_layout.removeWidget(old_widget)
            old_widget.deleteLater()
        
        # Create new widget
        task_widget = TaskWidget(task_data)
        self.task_widgets[task_id] = task_widget
        self.tasks_layout.insertWidget(0, task_widget)
    
    def _update_stats(self):
        """Update statistics display."""
        active = sum(1 for w in self.task_widgets.values() 
                    if w.findChild(QLabel).text() == "running")
        completed = sum(1 for w in self.task_widgets.values() 
                       if w.findChild(QLabel).text() == "completed")
        failed = sum(1 for w in self.task_widgets.values() 
                    if w.findChild(QLabel).text() == "failed")
        
        self.active_tasks.setText(f"Active Tasks: {active}")
        self.completed_tasks.setText(f"Completed: {completed}")
        self.failed_tasks.setText(f"Failed: {failed}")
    
    def handle_feedback(self, feedback_data: Dict):
        """Handle feedback from TaskExecutionStateMachine."""
        task_id = feedback_data['task_id']
        if feedback_data['event_type'] == 'task_started':
            self.signals.task_updated.emit(task_id, feedback_data['data']['plan'])
        elif feedback_data['event_type'] == 'step_completed':
            if task_id in self.task_widgets:
                task_data = feedback_data['data']
                self.signals.task_updated.emit(task_id, task_data)
        elif feedback_data['event_type'] == 'task_completed':
            self.signals.task_updated.emit(task_id, feedback_data['data']['plan'])

def create_monitor() -> TaskExecutionMonitor:
    """Create and show the task execution monitor."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    monitor = TaskExecutionMonitor()
    monitor.show()
    return monitor

if __name__ == "__main__":
    # Example usage
    monitor = create_monitor()
    
    # Simulate some task updates
    example_task = {
        "task_id": "test-task-1",
        "state": "running",
        "steps": [
            {
                "action": "wait_for_element",
                "element": "accept_button",
                "state": "completed",
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "result": {
                    "success": True,
                    "duration": 1.5
                }
            },
            {
                "action": "click",
                "element": "accept_button",
                "state": "running",
                "started_at": datetime.now().isoformat()
            }
        ]
    }
    
    monitor.handle_feedback({
        "task_id": "test-task-1",
        "event_type": "task_started",
        "data": {"plan": example_task}
    })
    
    sys.exit(app.exec_()) 