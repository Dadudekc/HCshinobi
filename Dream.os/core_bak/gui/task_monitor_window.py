"""Dream.OS Task Monitor Window Component."""

import sys
import json
from datetime import datetime
from typing import Dict, Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QScrollArea, QFrame, QPushButton,
    QMenuBar, QStatusBar, QDockWidget
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt5.QtGui import QColor, QPalette, QIcon, QFont

from core.gui.base_window import DreamOSWindow
from core.gui.theme import DreamTheme
from core.gui.widgets.task_widgets import TaskStepWidget, TaskWidget
from core.coordination.cursor.task_execution_state_machine import TaskState, StepState

class TaskMonitorWindow(DreamOSWindow):
    """Dream.OS Task Monitor Window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dream.OS Task Monitor")
        self.setObjectName("TaskMonitor")
        
        # Initialize window state
        self.task_widgets: Dict[str, TaskWidget] = {}
        
        # Setup UI
        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._setup_dock_widgets()
        
        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_stats)
        self.update_timer.start(1000)  # Update every second
        
        # Apply theme
        self.apply_theme()
    
    def _setup_ui(self):
        """Setup the main UI components."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)
        
        # Stats header
        stats_widget = QWidget()
        stats_widget.setObjectName("StatsWidget")
        self.stats_layout = QHBoxLayout()
        stats_widget.setLayout(self.stats_layout)
        
        self.active_tasks = QLabel("Active Tasks: 0")
        self.completed_tasks = QLabel("Completed: 0")
        self.failed_tasks = QLabel("Failed: 0")
        
        for label in [self.active_tasks, self.completed_tasks, self.failed_tasks]:
            label.setObjectName("StatsLabel")
            self.stats_layout.addWidget(label)
        
        self.stats_layout.addStretch()
        layout.addWidget(stats_widget)
        
        # Task container
        tasks_container = QWidget()
        tasks_container.setObjectName("TasksContainer")
        self.tasks_layout = QVBoxLayout()
        tasks_container.setLayout(self.tasks_layout)
        
        tasks_scroll = QScrollArea()
        tasks_scroll.setObjectName("TasksScroll")
        tasks_scroll.setWidget(tasks_container)
        tasks_scroll.setWidgetResizable(True)
        layout.addWidget(tasks_scroll)
    
    def _setup_menubar(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Save Log", self._save_log)
        file_menu.addAction("&Clear History", self._clear_history)
        file_menu.addSeparator()
        file_menu.addAction("&Exit", self.close)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("&Show Details", self._toggle_details)
        view_menu.addAction("&Auto Scroll", self._toggle_auto_scroll)
    
    def _setup_statusbar(self):
        """Setup the status bar."""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        self.status_message = QLabel("Ready")
        statusbar.addWidget(self.status_message)
        
        self.status_stats = QLabel()
        statusbar.addPermanentWidget(self.status_stats)
    
    def _setup_dock_widgets(self):
        """Setup dock widgets for additional views."""
        # Task Filter dock
        filter_dock = QDockWidget("Task Filters", self)
        filter_dock.setObjectName("FilterDock")
        filter_widget = QWidget()
        filter_layout = QVBoxLayout()
        filter_widget.setLayout(filter_layout)
        
        # Add filter controls here
        filter_dock.setWidget(filter_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, filter_dock)
    
    def apply_theme(self):
        """Apply Dream.OS theme to the window."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: """ + DreamTheme.BACKGROUND + """;
                color: """ + DreamTheme.TEXT + """;
            }
            #StatsWidget {
                background-color: """ + DreamTheme.SURFACE + """;
                border-radius: 4px;
                padding: 8px;
            }
            #StatsLabel {
                color: """ + DreamTheme.TEXT + """;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }
            #TasksScroll {
                border: none;
                background-color: transparent;
            }
            #TasksContainer {
                background-color: transparent;
            }
        """)
    
    def _update_stats(self):
        """Update statistics display."""
        active = sum(1 for w in self.task_widgets.values() 
                    if w.task_state == TaskState.RUNNING)
        completed = sum(1 for w in self.task_widgets.values() 
                       if w.task_state == TaskState.COMPLETED)
        failed = sum(1 for w in self.task_widgets.values() 
                    if w.task_state == TaskState.FAILED)
        
        self.active_tasks.setText(f"Active Tasks: {active}")
        self.completed_tasks.setText(f"Completed: {completed}")
        self.failed_tasks.setText(f"Failed: {failed}")
        
        self.status_stats.setText(
            f"Active: {active} | Completed: {completed} | Failed: {failed}"
        )
    
    def _save_log(self):
        """Save task execution log to file."""
        # TODO: Implement log saving
        self.status_message.setText("Log saved")
    
    def _clear_history(self):
        """Clear task execution history."""
        for widget in self.task_widgets.values():
            widget.deleteLater()
        self.task_widgets.clear()
        self._update_stats()
        self.status_message.setText("History cleared")
    
    def _toggle_details(self):
        """Toggle task detail view."""
        # TODO: Implement detail view toggling
        pass
    
    def _toggle_auto_scroll(self):
        """Toggle auto-scrolling to new tasks."""
        # TODO: Implement auto-scroll toggling
        pass
    
    def handle_task_update(self, task_id: str, task_data: Dict):
        """Handle task update from state machine."""
        if task_id in self.task_widgets:
            # Update existing widget
            self.task_widgets[task_id].update_data(task_data)
        else:
            # Create new widget
            task_widget = TaskWidget(task_data, self)
            self.task_widgets[task_id] = task_widget
            self.tasks_layout.insertWidget(0, task_widget)
        
        self._update_stats()
        self.status_message.setText(f"Updated task: {task_id}")

def create_monitor_window() -> TaskMonitorWindow:
    """Create and show the task monitor window."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    window = TaskMonitorWindow()
    window.show()
    return window

if __name__ == "__main__":
    # Example usage
    window = create_monitor_window()
    
    # Simulate task updates
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
    
    window.handle_task_update("test-task-1", example_task)
    sys.exit(app.exec_()) 