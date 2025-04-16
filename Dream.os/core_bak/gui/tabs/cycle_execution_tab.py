"""Dream.OS Cycle Execution Tab."""

from typing import Dict, List, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon

from core.task_manager import TaskManager
from core.feedback_engine import FeedbackEngine
from core.utils.logger import get_logger

# Get logger for this component
logger = get_logger(__name__, component="CycleExecutionTab")

class CycleStats:
    """Statistics for a task execution cycle."""
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_tasks: int = 0
        self.completed_tasks: int = 0
        self.failed_tasks: int = 0
        self.success_rate: float = 0.0

    def update(self, completed: int, failed: int, total: int):
        """Update cycle statistics."""
        self.completed_tasks = completed
        self.failed_tasks = failed
        self.total_tasks = total
        self.success_rate = (completed / total * 100) if total > 0 else 0

    def reset(self):
        """Reset statistics."""
        self.__init__()

class CycleExecutionTab(QWidget):
    """Tab for managing automated task cycles."""
    
    # Signals
    cycle_started = pyqtSignal(dict)  # cycle_config
    cycle_completed = pyqtSignal(dict)  # cycle_stats
    cycle_error = pyqtSignal(str)  # error_message
    
    def __init__(
        self,
        task_manager: TaskManager,
        feedback_engine: FeedbackEngine,
        parent=None
    ):
        super().__init__(parent)
        self.task_manager = task_manager
        self.feedback_engine = feedback_engine
        # Get logger specific to this instance/module
        self.logger = get_logger(__name__, component="CycleExecutionTab")
        
        # State
        self.cycle_stats = CycleStats()
        self.is_running = False
        self.current_template = None
        
        self._setup_ui()
        self._setup_signals()
        self._load_templates()
        
        # Refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._update_stats)
        self.refresh_timer.setInterval(1000)  # 1 second updates
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Control panel
        control_layout = QHBoxLayout()
        
        # Template selector
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(200)
        self.template_combo.setToolTip("Select the task template to execute")
        control_layout.addWidget(QLabel("Template:"))
        control_layout.addWidget(self.template_combo)
        
        # Cycle count
        self.cycle_count = QSpinBox()
        self.cycle_count.setRange(1, 1000)
        self.cycle_count.setValue(1)
        self.cycle_count.setToolTip("Set the number of times the template should run")
        control_layout.addWidget(QLabel("Cycles:"))
        control_layout.addWidget(self.cycle_count)
        
        # Control buttons
        self.start_btn = QPushButton("Start Cycle")
        self.start_btn.setIcon(QIcon("assets/icons/play.png"))
        self.start_btn.setToolTip("Start executing the selected template cycle")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setIcon(QIcon("assets/icons/stop.png"))
        self.stop_btn.setToolTip("Stop the currently running cycle")
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # Progress section
        progress_layout = QVBoxLayout()
        
        # Overall progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(QLabel("Overall Progress:"))
        progress_layout.addWidget(self.progress_bar)
        
        # Stats table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self._setup_stats_table()
        
        progress_layout.addWidget(QLabel("Cycle Statistics:"))
        progress_layout.addWidget(self.stats_table)
        
        layout.addLayout(progress_layout)
        
        # Task list
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels([
            "Task", "Status", "Duration", "Result"
        ])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(QLabel("Current Tasks:"))
        layout.addWidget(self.task_table)
        
        self.setLayout(layout)
    
    def _setup_stats_table(self):
        """Setup the statistics table."""
        self.stats_table.setRowCount(6)
        metrics = [
            "Start Time", "End Time", "Total Tasks",
            "Completed Tasks", "Failed Tasks", "Success Rate"
        ]
        for i, metric in enumerate(metrics):
            self.stats_table.setItem(i, 0, QTableWidgetItem(metric))
            self.stats_table.setItem(i, 1, QTableWidgetItem("-"))
    
    def _setup_signals(self):
        """Setup signal connections."""
        try:
            # Button connections
            self.start_btn.clicked.connect(self._start_cycle)
            self.stop_btn.clicked.connect(self._stop_cycle)
            
            # Template selection
            self.template_combo.currentIndexChanged.connect(
                self._template_selected
            )
            
            # Connect to task manager signals
            if self.task_manager:
                self.task_manager.task_completed.connect(
                    self._handle_task_completion
                )
                self.task_manager.task_failed.connect(
                    self._handle_task_failure
                )
        except Exception as e:
            self.logger.error(f"Error setting up signals: {e}")
            self._show_error("Failed to setup signal connections")
    
    def _load_templates(self):
        """Load available task templates."""
        try:
            templates = self.task_manager.get_templates()
            self.template_combo.clear()
            
            for template in templates:
                self.template_combo.addItem(
                    template.get("name", "Unnamed"),
                    template
                )
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
            self._show_error("Failed to load task templates")
    
    def _template_selected(self, index: int):
        """Handle template selection."""
        try:
            self.current_template = self.template_combo.itemData(index)
            if self.current_template:
                self._update_task_table()
        except Exception as e:
            self.logger.error(f"Error selecting template: {e}")
    
    def _start_cycle(self):
        """Start task execution cycle."""
        try:
            if not self.current_template:
                self._show_error("Please select a task template")
                return
            
            self.is_running = True
            self.cycle_stats.reset()
            self.cycle_stats.start_time = datetime.now()
            
            # Update UI
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.template_combo.setEnabled(False)
            self.cycle_count.setEnabled(False)
            
            # Start execution
            cycle_config = {
                "template": self.current_template,
                "cycles": self.cycle_count.value()
            }
            
            self.task_manager.start_cycle(cycle_config)
            self.refresh_timer.start()
            
            # Emit signal
            self.cycle_started.emit(cycle_config)
            
            self._log_event("cycle_started", cycle_config)
        except Exception as e:
            self.logger.error(f"Error starting cycle: {e}")
            self._show_error("Failed to start task cycle")
            self._stop_cycle()
    
    def _stop_cycle(self):
        """Stop task execution cycle."""
        try:
            self.is_running = False
            self.refresh_timer.stop()
            
            if self.cycle_stats.start_time:
                self.cycle_stats.end_time = datetime.now()
            
            # Update UI
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.template_combo.setEnabled(True)
            self.cycle_count.setEnabled(True)
            
            # Stop execution
            self.task_manager.stop_cycle()
            
            # Emit signal
            self.cycle_completed.emit(self.cycle_stats.__dict__)
            
            self._log_event("cycle_stopped", {
                "stats": self.cycle_stats.__dict__
            })
        except Exception as e:
            self.logger.error(f"Error stopping cycle: {e}")
            self._show_error("Failed to stop task cycle")
    
    def _update_stats(self):
        """Update cycle statistics."""
        try:
            if not self.is_running:
                return
            
            stats = self.task_manager.get_cycle_stats()
            self.cycle_stats.update(
                completed=stats.get("completed", 0),
                failed=stats.get("failed", 0),
                total=stats.get("total", 0)
            )
            
            # Update progress bar
            progress = (
                (self.cycle_stats.completed_tasks + self.cycle_stats.failed_tasks)
                / self.cycle_stats.total_tasks * 100
            ) if self.cycle_stats.total_tasks > 0 else 0
            self.progress_bar.setValue(int(progress))
            
            # Update stats table
            self._update_stats_table()
            
            # Update task table
            self._update_task_table()
        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")
    
    def _update_stats_table(self):
        """Update the statistics table."""
        try:
            stats = [
                self.cycle_stats.start_time.strftime("%H:%M:%S")
                if self.cycle_stats.start_time else "-",
                self.cycle_stats.end_time.strftime("%H:%M:%S")
                if self.cycle_stats.end_time else "-",
                str(self.cycle_stats.total_tasks),
                str(self.cycle_stats.completed_tasks),
                str(self.cycle_stats.failed_tasks),
                f"{self.cycle_stats.success_rate:.1f}%"
            ]
            
            for i, value in enumerate(stats):
                self.stats_table.setItem(i, 1, QTableWidgetItem(value))
        except Exception as e:
            self.logger.error(f"Error updating stats table: {e}")
    
    def _update_task_table(self):
        """Update the task execution table."""
        try:
            if not self.current_template:
                return
            
            tasks = self.task_manager.get_current_tasks()
            self.task_table.setRowCount(len(tasks))
            
            for i, task in enumerate(tasks):
                self.task_table.setItem(
                    i, 0, QTableWidgetItem(task.get("name", ""))
                )
                self.task_table.setItem(
                    i, 1, QTableWidgetItem(task.get("status", ""))
                )
                self.task_table.setItem(
                    i, 2, QTableWidgetItem(
                        f"{task.get('duration', 0):.2f}s"
                    )
                )
                self.task_table.setItem(
                    i, 3, QTableWidgetItem(task.get("result", ""))
                )
        except Exception as e:
            self.logger.error(f"Error updating task table: {e}")
    
    def _handle_task_completion(self, task_data: Dict):
        """Handle task completion event."""
        try:
            self._log_event("task_completed", task_data)
            self._update_stats()
        except Exception as e:
            self.logger.error(f"Error handling task completion: {e}")
    
    def _handle_task_failure(self, task_data: Dict):
        """Handle task failure event."""
        try:
            self._log_event("task_failed", task_data)
            self._update_stats()
            
            # Show error if configured
            if self.current_template.get("stop_on_error", False):
                self._stop_cycle()
                self._show_error(
                    f"Task failed: {task_data.get('error', 'Unknown error')}"
                )
        except Exception as e:
            self.logger.error(f"Error handling task failure: {e}")
    
    def _show_error(self, message: str):
        """Show error message dialog."""
        QMessageBox.critical(self, "Error", message)
        self.cycle_error.emit(message)
    
    def _log_event(self, event_type: str, data: Dict):
        """Log event to feedback engine."""
        try:
            if self.feedback_engine:
                self.feedback_engine.log_event(
                    event_type,
                    {
                        "source": "cycle_execution",
                        **data
                    }
                )
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def refresh_state(self):
        """Refresh tab state."""
        try:
            self._load_templates()
            self._update_stats()
        except Exception as e:
            self.logger.error(f"Error refreshing state: {e}")

    def get_state(self) -> dict:
        """Get the current state of the tab for persistence."""
        try:
            current_tasks = []
            for row in range(self.task_table.rowCount()):
                current_tasks.append({
                    "name": self.task_table.item(row, 0).text(),
                    "status": self.task_table.item(row, 1).text(),
                    "duration": float(self.task_table.item(row, 2).text().rstrip("s")),
                    "result": self.task_table.item(row, 3).text()
                })

            return {
                "is_running": self.is_running,
                "current_template": self.current_template,
                "cycle_count": self.cycle_count.value(),
                "cycle_stats": {
                    "start_time": self.cycle_stats.start_time.isoformat() if self.cycle_stats.start_time else None,
                    "end_time": self.cycle_stats.end_time.isoformat() if self.cycle_stats.end_time else None,
                    "total_tasks": self.cycle_stats.total_tasks,
                    "completed_tasks": self.cycle_stats.completed_tasks,
                    "failed_tasks": self.cycle_stats.failed_tasks,
                    "success_rate": self.cycle_stats.success_rate
                },
                "current_tasks": current_tasks,
                "selected_template_index": self.template_combo.currentIndex()
            }
        except Exception as e:
            self.logger.error(f"Error getting tab state: {e}")
            return {}

    def restore_state(self, state: dict):
        """Restore the tab state from persistence."""
        try:
            if not state:
                return

            # Restore template selection
            if state.get("selected_template_index") is not None:
                self.template_combo.setCurrentIndex(state["selected_template_index"])
                if state.get("current_template"):
                    self.current_template = state["current_template"]

            # Restore cycle count
            if state.get("cycle_count"):
                self.cycle_count.setValue(state["cycle_count"])

            # Restore cycle stats
            if state.get("cycle_stats"):
                stats = state["cycle_stats"]
                self.cycle_stats.total_tasks = stats.get("total_tasks", 0)
                self.cycle_stats.completed_tasks = stats.get("completed_tasks", 0)
                self.cycle_stats.failed_tasks = stats.get("failed_tasks", 0)
                self.cycle_stats.success_rate = stats.get("success_rate", 0.0)
                
                if stats.get("start_time"):
                    self.cycle_stats.start_time = datetime.fromisoformat(stats["start_time"])
                if stats.get("end_time"):
                    self.cycle_stats.end_time = datetime.fromisoformat(stats["end_time"])

            # Restore task table
            if state.get("current_tasks"):
                self._update_task_table(state["current_tasks"])

            # Restore running state (if was running, will need manual restart)
            self.is_running = False  # Always start stopped for safety
            self._update_ui_state()
            
            if state.get("is_running"):
                self._show_error("Cycle execution was running during last shutdown. Manual restart required.")

            self._log_event("state_restored", {"success": True})
        except Exception as e:
            self.logger.error(f"Error restoring tab state: {e}")
            self._log_event("state_restored", {"success": False, "error": str(e)})

    def prepare_for_shutdown(self):
        """Prepare the tab for system shutdown."""
        try:
            # Stop any running cycle
            if self.is_running:
                self._stop_cycle()

            # Stop the refresh timer
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()

            # Log final statistics
            stats = {
                "was_running": self.is_running,
                "template": self.current_template.get("name") if self.current_template else None,
                "cycle_stats": {
                    "total_tasks": self.cycle_stats.total_tasks,
                    "completed_tasks": self.cycle_stats.completed_tasks,
                    "failed_tasks": self.cycle_stats.failed_tasks,
                    "success_rate": self.cycle_stats.success_rate
                }
            }
            self._log_event("tab_shutdown", stats)

            # Return success to indicate clean shutdown
            return True
        except Exception as e:
            self.logger.error(f"Error preparing for shutdown: {e}")
            return False

    def _update_ui_state(self):
        """Update UI elements based on running state."""
        self.start_btn.setEnabled(not self.is_running)
        self.stop_btn.setEnabled(self.is_running)
        self.template_combo.setEnabled(not self.is_running)
        self.cycle_count.setEnabled(not self.is_running) 