"""Dream.OS Tab Manager."""

from typing import Optional, Dict, Any
from PyQt5.QtWidgets import QTabWidget, QWidget, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

from core.gui.theme import DreamTheme
from core.gui.tabs.task_monitor_tab import TaskMonitorTab
from core.gui.tabs.cycle_execution_tab import CycleExecutionTab
from core.gui.tabs.feedback_tab import FeedbackTab
from core.task_manager import TaskManager
from core.feedback_engine import FeedbackEngine
from core.utils.logger import get_logger

logger = get_logger(__name__)

class DreamOSTabManager(QTabWidget):
    """Main tab manager for Dream.OS."""
    
    # Signals
    tab_state_changed = pyqtSignal(str, dict)  # tab_id, state
    
    def __init__(
        self,
        task_manager: TaskManager,
        feedback_engine: FeedbackEngine,
        parent=None
    ):
        super().__init__(parent)
        self.setObjectName("DreamOSTabManager")
        
        self.task_manager = task_manager
        self.feedback_engine = feedback_engine
        self.logger = get_logger(__name__)
        
        # Track tab states
        self.tab_states: Dict[str, Any] = {}
        
        self._setup_tabs()
        self._setup_signals()
        self.apply_theme()
        
        # Log initialization
        self._log_event("tab_manager_initialized", {
            "active_tabs": self.count()
        })
    
    def _setup_tabs(self):
        """Setup the tab structure."""
        try:
            # Task Monitor tab
            self.task_monitor = TaskMonitorTab(
                self.task_manager,
                self.feedback_engine
            )
            self.addTab(self.task_monitor, "Task Monitor")
            self.tab_states["task_monitor"] = {
                "active": True,
                "last_refresh": None
            }
            
            # Cycle Execution tab
            self.cycle_tab = CycleExecutionTab(
                self.task_manager,
                self.feedback_engine
            )
            self.addTab(self.cycle_tab, "Cycle Execution")
            self.tab_states["cycle_execution"] = {
                "active": True,
                "current_cycle": None
            }
            
            # Feedback tab
            self.feedback_tab = FeedbackTab(
                self.feedback_engine
            )
            self.addTab(self.feedback_tab, "Feedback")
            self.tab_states["feedback"] = {
                "active": True,
                "unread_count": 0
            }
            
            # Set icons
            self.setTabIcon(0, QIcon("assets/icons/tasks.png"))
            self.setTabIcon(1, QIcon("assets/icons/cycle.png"))
            self.setTabIcon(2, QIcon("assets/icons/feedback.png"))
            
            # Set default tab
            self.setCurrentIndex(0)
            
        except Exception as e:
            self.logger.error(f"Error setting up tabs: {e}")
            QMessageBox.critical(
                self,
                "Initialization Error",
                "Failed to initialize tabs. Check logs for details."
            )
    
    def _setup_signals(self):
        """Setup signal connections."""
        try:
            # Connect tab changes
            self.currentChanged.connect(self._handle_tab_change)
            
            # Connect feedback updates
            if self.feedback_engine:
                self.feedback_engine.event_received.connect(
                    self._handle_feedback
                )
        except Exception as e:
            self.logger.error(f"Error setting up signals: {e}")
    
    def _handle_tab_change(self, index: int):
        """Handle tab change events."""
        try:
            tab_name = self.tabText(index).lower().replace(" ", "_")
            
            # Update tab state
            if tab_name in self.tab_states:
                self.tab_states[tab_name]["active"] = True
                
                # Emit state change
                self.tab_state_changed.emit(
                    tab_name,
                    self.tab_states[tab_name]
                )
                
                # Log event
                self._log_event("tab_activated", {
                    "tab": tab_name,
                    "index": index
                })
                
                # Refresh tab content
                self.refresh_tab(tab_name)
        except Exception as e:
            self.logger.error(f"Error handling tab change: {e}")
    
    def _handle_feedback(self, event_data: Dict):
        """Handle feedback engine events."""
        try:
            # Update unread count
            if "feedback" in self.tab_states:
                self.tab_states["feedback"]["unread_count"] += 1
                
                # Update tab text to show unread count
                unread = self.tab_states["feedback"]["unread_count"]
                self.setTabText(2, f"Feedback ({unread})")
                
                # Emit state change
                self.tab_state_changed.emit(
                    "feedback",
                    self.tab_states["feedback"]
                )
        except Exception as e:
            self.logger.error(f"Error handling feedback: {e}")
    
    def refresh_tab(self, tab_name: str):
        """Refresh specific tab content."""
        try:
            if tab_name == "task_monitor" and hasattr(self, 'task_monitor'):
                self.task_monitor._refresh_tasks()
                self.tab_states[tab_name]["last_refresh"] = datetime.now()
            
            elif tab_name == "cycle_execution" and hasattr(self, 'cycle_tab'):
                self.cycle_tab.refresh_state()
                
            elif tab_name == "feedback" and hasattr(self, 'feedback_tab'):
                self.feedback_tab.refresh_events()
                # Reset unread count
                self.tab_states[tab_name]["unread_count"] = 0
                self.setTabText(2, "Feedback")
        except Exception as e:
            self.logger.error(f"Error refreshing tab {tab_name}: {e}")
    
    def refresh_all(self):
        """Refresh all tabs."""
        try:
            for tab_name in self.tab_states:
                if self.tab_states[tab_name]["active"]:
                    self.refresh_tab(tab_name)
            
            self._log_event("tabs_refreshed", {
                "active_tabs": [
                    name for name, state in self.tab_states.items()
                    if state["active"]
                ]
            })
        except Exception as e:
            self.logger.error(f"Error refreshing tabs: {e}")
    
    def _log_event(self, event_type: str, data: Dict):
        """Log event to feedback engine."""
        try:
            if self.feedback_engine:
                self.feedback_engine.log_event(
                    event_type,
                    {
                        "source": "tab_manager",
                        **data
                    }
                )
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def apply_theme(self):
        """Apply Dream.OS theme."""
        self.setStyleSheet(DreamTheme.get_tab_style())
    
    def closeEvent(self, event):
        """Handle tab manager closing."""
        try:
            # Stop any active timers
            if hasattr(self, 'task_monitor'):
                self.task_monitor.refresh_timer.stop()
            
            # Log closure
            self._log_event("tab_manager_closed", {
                "tab_states": self.tab_states
            })
            
            super().closeEvent(event)
        except Exception as e:
            self.logger.error(f"Error during close: {e}")
            event.accept()  # Ensure window closes even if error occurs 