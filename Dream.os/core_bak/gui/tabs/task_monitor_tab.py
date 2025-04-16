"""Dream.OS Task Monitor Tab."""

from typing import Dict, List, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QLineEdit, QMessageBox, QMenu
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QColor

from core.task_manager import TaskManager
from core.feedback_engine import FeedbackEngine
from core.utils.logger import get_logger

# Get logger for this component
logger = get_logger(__name__, component="TaskMonitorTab")

class TaskStatus:
    """Task status constants."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskMonitorTab(QWidget):
    """Tab for monitoring and managing tasks."""
    
    # Signals
    task_selected = pyqtSignal(dict)  # task_data
    task_action = pyqtSignal(str, dict)  # action, task_data
    
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
        self.logger = get_logger(__name__, component="TaskMonitorTab")
        
        # State
        self.selected_task = None
        self.filter_status = None
        self.search_text = ""
        
        self._setup_ui()
        self._setup_signals()
        
        # Refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_tasks)
        self.refresh_timer.setInterval(2000)  # 2 second updates
        self.refresh_timer.start()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Filter bar
        filter_layout = QHBoxLayout()
        
        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItem("All Status")
        self.status_filter.addItems([
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED
        ])
        self.status_filter.setToolTip("Filter tasks by their current status")
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tasks...")
        self.search_box.setToolTip("Filter tasks by ID or name")
        filter_layout.addWidget(self.search_box)
        
        # Refresh button
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(QIcon("assets/icons/refresh.png"))
        self.refresh_btn.setToolTip("Refresh Tasks")
        filter_layout.addWidget(self.refresh_btn)
        
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Task table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels([
            "ID", "Name", "Status", "Progress",
            "Start Time", "Duration", "Result"
        ])
        self.task_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.task_table)
        
        # Details section
        details_layout = QHBoxLayout()
        
        # Task details
        self.details_label = QLabel("No task selected")
        details_layout.addWidget(self.details_label)
        
        # Action buttons
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(QIcon("assets/icons/cancel.png"))
        self.cancel_btn.setToolTip("Cancel the selected running task")
        self.cancel_btn.setEnabled(False)
        
        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setIcon(QIcon("assets/icons/retry.png"))
        self.retry_btn.setToolTip("Retry the selected failed task")
        self.retry_btn.setEnabled(False)
        
        details_layout.addWidget(self.cancel_btn)
        details_layout.addWidget(self.retry_btn)
        
        layout.addLayout(details_layout)
        
        self.setLayout(layout)
    
    def _setup_signals(self):
        """Setup signal connections."""
        try:
            # UI signals
            self.status_filter.currentTextChanged.connect(
                self._handle_filter_change
            )
            self.search_box.textChanged.connect(self._handle_search_change)
            self.refresh_btn.clicked.connect(self._manual_refresh)
            
            # Table signals
            self.task_table.itemSelectionChanged.connect(
                self._handle_selection_change
            )
            self.task_table.customContextMenuRequested.connect(
                self._show_context_menu
            )
            
            # Action buttons
            self.cancel_btn.clicked.connect(self._cancel_selected_task)
            self.retry_btn.clicked.connect(self._retry_selected_task)
            
            # Task manager signals
            if self.task_manager:
                self.task_manager.task_started.connect(
                    self._handle_task_started
                )
                self.task_manager.task_completed.connect(
                    self._handle_task_completed
                )
                self.task_manager.task_failed.connect(
                    self._handle_task_failed
                )
                self.task_manager.task_cancelled.connect(
                    self._handle_task_cancelled
                )
        except Exception as e:
            self.logger.error(f"Error setting up signals: {e}")
            self._show_error("Failed to setup signal connections")
    
    def _refresh_tasks(self):
        """Refresh the task list."""
        try:
            tasks = self.task_manager.get_tasks()
            filtered_tasks = self._filter_tasks(tasks)
            self._update_task_table(filtered_tasks)
            
            if self.selected_task:
                self._update_selected_task()
        except Exception as e:
            self.logger.error(f"Error refreshing tasks: {e}")
    
    def _filter_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Filter tasks based on current filters."""
        try:
            filtered = tasks
            
            # Status filter
            if self.filter_status and self.filter_status != "All Status":
                filtered = [
                    task for task in filtered
                    if task.get("status") == self.filter_status
                ]
            
            # Search filter
            if self.search_text:
                search_lower = self.search_text.lower()
                filtered = [
                    task for task in filtered
                    if search_lower in task.get("name", "").lower()
                    or search_lower in task.get("id", "").lower()
                ]
            
            return filtered
        except Exception as e:
            self.logger.error(f"Error filtering tasks: {e}")
            return []
    
    def _update_task_table(self, tasks: List[Dict]):
        """Update the task table with filtered tasks."""
        try:
            self.task_table.setRowCount(len(tasks))
            
            for i, task in enumerate(tasks):
                # ID
                self.task_table.setItem(
                    i, 0, QTableWidgetItem(task.get("id", ""))
                )
                
                # Name
                self.task_table.setItem(
                    i, 1, QTableWidgetItem(task.get("name", ""))
                )
                
                # Status
                status_item = QTableWidgetItem(task.get("status", ""))
                status_color = self._get_status_color(task.get("status"))
                if status_color:
                    status_item.setBackground(status_color)
                self.task_table.setItem(i, 2, status_item)
                
                # Progress
                progress = task.get("progress", 0)
                self.task_table.setItem(
                    i, 3, QTableWidgetItem(f"{progress}%")
                )
                
                # Start Time
                start_time = task.get("start_time")
                if start_time:
                    if isinstance(start_time, str):
                        time_str = start_time
                    else:
                        time_str = start_time.strftime("%H:%M:%S")
                else:
                    time_str = "-"
                self.task_table.setItem(i, 4, QTableWidgetItem(time_str))
                
                # Duration
                duration = task.get("duration", 0)
                self.task_table.setItem(
                    i, 5, QTableWidgetItem(f"{duration:.2f}s")
                )
                
                # Result
                result = task.get("result", "")
                if isinstance(result, dict):
                    result = str(result)
                self.task_table.setItem(i, 6, QTableWidgetItem(result))
        except Exception as e:
            self.logger.error(f"Error updating task table: {e}")
    
    def _get_status_color(self, status: str) -> Optional[QColor]:
        """Get color for task status."""
        colors = {
            TaskStatus.PENDING: QColor(255, 255, 224),  # Light yellow
            TaskStatus.RUNNING: QColor(176, 224, 230),  # Powder blue
            TaskStatus.COMPLETED: QColor(144, 238, 144),  # Light green
            TaskStatus.FAILED: QColor(255, 182, 193),  # Light pink
            TaskStatus.CANCELLED: QColor(211, 211, 211)  # Light gray
        }
        return colors.get(status)
    
    def _handle_filter_change(self, status: str):
        """Handle status filter change."""
        try:
            self.filter_status = status
            self._refresh_tasks()
        except Exception as e:
            self.logger.error(f"Error handling filter change: {e}")
    
    def _handle_search_change(self, text: str):
        """Handle search text change."""
        try:
            self.search_text = text
            self._refresh_tasks()
        except Exception as e:
            self.logger.error(f"Error handling search change: {e}")
    
    def _handle_selection_change(self):
        """Handle task selection change."""
        try:
            selected_items = self.task_table.selectedItems()
            if not selected_items:
                self.selected_task = None
                self.details_label.setText("No task selected")
                self.cancel_btn.setEnabled(False)
                self.retry_btn.setEnabled(False)
                return
            
            row = selected_items[0].row()
            task_id = self.task_table.item(row, 0).text()
            self.selected_task = self.task_manager.get_task(task_id)
            
            if self.selected_task:
                self._update_selected_task()
                self.task_selected.emit(self.selected_task)
        except Exception as e:
            self.logger.error(f"Error handling selection change: {e}")
    
    def _update_selected_task(self):
        """Update UI for selected task."""
        try:
            if not self.selected_task:
                return
            
            # Update details label
            details = (
                f"Task: {self.selected_task.get('name')}\n"
                f"Status: {self.selected_task.get('status')}\n"
                f"Progress: {self.selected_task.get('progress')}%"
            )
            self.details_label.setText(details)
            
            # Update action buttons
            status = self.selected_task.get("status")
            self.cancel_btn.setEnabled(
                status in [TaskStatus.PENDING, TaskStatus.RUNNING]
            )
            self.retry_btn.setEnabled(
                status in [TaskStatus.FAILED, TaskStatus.CANCELLED]
            )
        except Exception as e:
            self.logger.error(f"Error updating selected task: {e}")
    
    def _show_context_menu(self, position):
        """Show context menu for task table."""
        try:
            if not self.selected_task:
                return
            
            menu = QMenu()
            
            # Add actions based on task status
            status = self.selected_task.get("status")
            
            if status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                cancel_action = menu.addAction(
                    QIcon("assets/icons/cancel.png"),
                    "Cancel"
                )
                cancel_action.triggered.connect(self._cancel_selected_task)
            
            if status in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                retry_action = menu.addAction(
                    QIcon("assets/icons/retry.png"),
                    "Retry"
                )
                retry_action.triggered.connect(self._retry_selected_task)
            
            # Show menu
            menu.exec_(self.task_table.mapToGlobal(position))
        except Exception as e:
            self.logger.error(f"Error showing context menu: {e}")
    
    def _cancel_selected_task(self):
        """Cancel the selected task."""
        try:
            if not self.selected_task:
                return
            
            task_id = self.selected_task.get("id")
            if not task_id:
                return
            
            self.task_manager.cancel_task(task_id)
            self.task_action.emit("cancel", self.selected_task)
            self._log_event("task_cancelled", self.selected_task)
        except Exception as e:
            self.logger.error(f"Error cancelling task: {e}")
            self._show_error("Failed to cancel task")
    
    def _retry_selected_task(self):
        """Retry the selected task."""
        try:
            if not self.selected_task:
                return
            
            task_id = self.selected_task.get("id")
            if not task_id:
                return
            
            self.task_manager.retry_task(task_id)
            self.task_action.emit("retry", self.selected_task)
            self._log_event("task_retried", self.selected_task)
        except Exception as e:
            self.logger.error(f"Error retrying task: {e}")
            self._show_error("Failed to retry task")
    
    def _manual_refresh(self):
        """Handle manual refresh button click."""
        try:
            self._refresh_tasks()
            self._log_event("manual_refresh", {})
        except Exception as e:
            self.logger.error(f"Error during manual refresh: {e}")
    
    def _handle_task_started(self, task_data: Dict):
        """Handle task started event."""
        try:
            self._log_event("task_started", task_data)
            self._refresh_tasks()
        except Exception as e:
            self.logger.error(f"Error handling task start: {e}")
    
    def _handle_task_completed(self, task_data: Dict):
        """Handle task completed event."""
        try:
            self._log_event("task_completed", task_data)
            self._refresh_tasks()
        except Exception as e:
            self.logger.error(f"Error handling task completion: {e}")
    
    def _handle_task_failed(self, task_data: Dict):
        """Handle task failed event."""
        try:
            self._log_event("task_failed", task_data)
            self._refresh_tasks()
        except Exception as e:
            self.logger.error(f"Error handling task failure: {e}")
    
    def _handle_task_cancelled(self, task_data: Dict):
        """Handle task cancelled event."""
        try:
            self._log_event("task_cancelled", task_data)
            self._refresh_tasks()
        except Exception as e:
            self.logger.error(f"Error handling task cancellation: {e}")
    
    def _show_error(self, message: str):
        """Show error message dialog."""
        QMessageBox.critical(self, "Error", message)
    
    def _log_event(self, event_type: str, data: Dict):
        """Log event to feedback engine."""
        try:
            if self.feedback_engine:
                self.feedback_engine.log_event(
                    event_type,
                    {
                        "source": "task_monitor",
                        **data
                    }
                )
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def refresh_state(self):
        """Refresh tab state."""
        try:
            self._refresh_tasks()
        except Exception as e:
            self.logger.error(f"Error refreshing state: {e}")

    def get_state(self) -> dict:
        """Get the current state of the tab for persistence."""
        try:
            return {
                "filter_status": self.filter_status,
                "search_text": self.search_text,
                "selected_task_id": self.selected_task.get("id") if self.selected_task else None,
                "visible_tasks": [
                    {
                        "id": self.task_table.item(row, 0).text(),
                        "name": self.task_table.item(row, 1).text(),
                        "status": self.task_table.item(row, 2).text(),
                        "progress": self.task_table.item(row, 3).text().rstrip("%"),
                        "start_time": self.task_table.item(row, 4).text(),
                        "duration": float(self.task_table.item(row, 5).text().rstrip("s")),
                        "result": self.task_table.item(row, 6).text()
                    }
                    for row in range(self.task_table.rowCount())
                ]
            }
        except Exception as e:
            self.logger.error(f"Error getting tab state: {e}")
            return {}

    def restore_state(self, state: dict):
        """Restore the tab state from persistence."""
        try:
            if not state:
                return

            # Restore filters
            if state.get("filter_status"):
                self.status_filter.setCurrentText(state["filter_status"])
                self.filter_status = state["filter_status"]
            
            if state.get("search_text"):
                self.search_box.setText(state["search_text"])
                self.search_text = state["search_text"]

            # Restore visible tasks
            if state.get("visible_tasks"):
                self._update_task_table(state["visible_tasks"])

            # Restore selection if task still exists
            if state.get("selected_task_id"):
                for row in range(self.task_table.rowCount()):
                    if self.task_table.item(row, 0).text() == state["selected_task_id"]:
                        self.task_table.selectRow(row)
                        break

            self._log_event("state_restored", {"success": True})
        except Exception as e:
            self.logger.error(f"Error restoring tab state: {e}")
            self._log_event("state_restored", {"success": False, "error": str(e)})

    def prepare_for_shutdown(self):
        """Prepare the tab for system shutdown."""
        try:
            # Stop the refresh timer
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()

            # Log final statistics
            stats = {
                "total_tasks": self.task_table.rowCount(),
                "filtered_status": self.filter_status,
                "search_criteria": self.search_text,
                "selected_task": self.selected_task.get("id") if self.selected_task else None
            }
            self._log_event("tab_shutdown", stats)

            # Return success to indicate clean shutdown
            return True
        except Exception as e:
            self.logger.error(f"Error preparing for shutdown: {e}")
            return False 