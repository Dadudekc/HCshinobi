"""Dream.OS Feedback Tab."""

from typing import Dict, List, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QLineEdit, QMessageBox, QMenu,
    QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QColor

from core.feedback_engine import FeedbackEngine
from core.utils.logger import get_logger

# Get logger for this component
logger = get_logger(__name__, component="FeedbackTab")

class EventSeverity:
    """Event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

class FeedbackTab(QWidget):
    """Tab for displaying system feedback and events."""
    
    # Signals
    event_selected = pyqtSignal(dict)  # event_data
    event_action = pyqtSignal(str, dict)  # action, event_data
    
    def __init__(
        self,
        feedback_engine: FeedbackEngine,
        parent=None
    ):
        super().__init__(parent)
        self.feedback_engine = feedback_engine
        # Get logger specific to this instance/module
        self.logger = get_logger(__name__, component="FeedbackTab")
        
        # State
        self.selected_event = None
        self.filter_source = None
        self.filter_severity = None
        self.search_text = ""
        
        self._setup_ui()
        self._setup_signals()
        
        # Refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_events)
        self.refresh_timer.setInterval(2000)  # 2 second updates
        self.refresh_timer.start()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Filter bar
        filter_layout = QHBoxLayout()
        
        # Source filter
        self.source_filter = QComboBox()
        self.source_filter.addItem("All Sources")
        self.source_filter.setToolTip("Filter events by their source component")
        filter_layout.addWidget(QLabel("Source:"))
        filter_layout.addWidget(self.source_filter)
        
        # Severity filter
        self.severity_filter = QComboBox()
        self.severity_filter.addItem("All Severities")
        self.severity_filter.addItems([
            EventSeverity.INFO,
            EventSeverity.WARNING,
            EventSeverity.ERROR,
            EventSeverity.SUCCESS
        ])
        self.severity_filter.setToolTip("Filter events by their severity level")
        filter_layout.addWidget(QLabel("Severity:"))
        filter_layout.addWidget(self.severity_filter)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search events...")
        self.search_box.setToolTip("Filter events by message or type")
        filter_layout.addWidget(self.search_box)
        
        # Refresh button
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(QIcon("assets/icons/refresh.png"))
        self.refresh_btn.setToolTip("Refresh Events")
        filter_layout.addWidget(self.refresh_btn)
        
        # Clear button
        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(QIcon("assets/icons/clear.png"))
        self.clear_btn.setToolTip("Clear all events from the list")
        filter_layout.addWidget(self.clear_btn)
        
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Create splitter for events and details
        splitter = QSplitter(Qt.Vertical)
        
        # Events table
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(5)
        self.events_table.setHorizontalHeaderLabels([
            "Time", "Source", "Type", "Severity", "Message"
        ])
        self.events_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.events_table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.events_table)
        
        # Event details
        details_widget = QWidget()
        details_layout = QVBoxLayout()
        details_widget.setLayout(details_layout)
        
        details_layout.addWidget(QLabel("Event Details:"))
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        splitter.addWidget(details_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 100])
        
        layout.addWidget(splitter)
        
        self.setLayout(layout)
    
    def _setup_signals(self):
        """Setup signal connections."""
        try:
            # UI signals
            self.source_filter.currentTextChanged.connect(
                self._handle_source_change
            )
            self.severity_filter.currentTextChanged.connect(
                self._handle_severity_change
            )
            self.search_box.textChanged.connect(self._handle_search_change)
            self.refresh_btn.clicked.connect(self._manual_refresh)
            self.clear_btn.clicked.connect(self._clear_events)
            
            # Table signals
            self.events_table.itemSelectionChanged.connect(
                self._handle_selection_change
            )
            self.events_table.customContextMenuRequested.connect(
                self._show_context_menu
            )
            
            # Feedback engine signals
            if self.feedback_engine:
                self.feedback_engine.event_received.connect(
                    self._handle_new_event
                )
        except Exception as e:
            self.logger.error(f"Error setting up signals: {e}")
            self._show_error("Failed to setup signal connections")
    
    def _refresh_events(self):
        """Refresh the events list."""
        try:
            events = self.feedback_engine.get_events()
            filtered_events = self._filter_events(events)
            self._update_events_table(filtered_events)
            self._update_source_filter(events)
            
            if self.selected_event:
                self._update_selected_event()
        except Exception as e:
            self.logger.error(f"Error refreshing events: {e}")
    
    def _filter_events(self, events: List[Dict]) -> List[Dict]:
        """Filter events based on current filters."""
        try:
            filtered = events
            
            # Source filter
            if self.filter_source and self.filter_source != "All Sources":
                filtered = [
                    event for event in filtered
                    if event.get("source") == self.filter_source
                ]
            
            # Severity filter
            if self.filter_severity and self.filter_severity != "All Severities":
                filtered = [
                    event for event in filtered
                    if event.get("severity") == self.filter_severity
                ]
            
            # Search filter
            if self.search_text:
                search_lower = self.search_text.lower()
                filtered = [
                    event for event in filtered
                    if search_lower in event.get("message", "").lower()
                    or search_lower in event.get("type", "").lower()
                ]
            
            return filtered
        except Exception as e:
            self.logger.error(f"Error filtering events: {e}")
            return []
    
    def _update_events_table(self, events: List[Dict]):
        """Update the events table with filtered events."""
        try:
            self.events_table.setRowCount(len(events))
            
            for i, event in enumerate(events):
                # Time
                time = event.get("timestamp")
                if isinstance(time, datetime):
                    time_str = time.strftime("%H:%M:%S")
                else:
                    time_str = str(time)
                self.events_table.setItem(i, 0, QTableWidgetItem(time_str))
                
                # Source
                self.events_table.setItem(
                    i, 1, QTableWidgetItem(event.get("source", ""))
                )
                
                # Type
                self.events_table.setItem(
                    i, 2, QTableWidgetItem(event.get("type", ""))
                )
                
                # Severity
                severity_item = QTableWidgetItem(event.get("severity", ""))
                severity_color = self._get_severity_color(
                    event.get("severity")
                )
                if severity_color:
                    severity_item.setBackground(severity_color)
                self.events_table.setItem(i, 3, severity_item)
                
                # Message
                self.events_table.setItem(
                    i, 4, QTableWidgetItem(event.get("message", ""))
                )
        except Exception as e:
            self.logger.error(f"Error updating events table: {e}")
    
    def _get_severity_color(self, severity: str) -> Optional[QColor]:
        """Get color for event severity."""
        colors = {
            EventSeverity.INFO: QColor(176, 224, 230),  # Light blue
            EventSeverity.WARNING: QColor(255, 255, 224),  # Light yellow
            EventSeverity.ERROR: QColor(255, 182, 193),  # Light red
            EventSeverity.SUCCESS: QColor(144, 238, 144)  # Light green
        }
        return colors.get(severity)
    
    def _update_source_filter(self, events: List[Dict]):
        """Update source filter options."""
        try:
            current = self.source_filter.currentText()
            
            # Get unique sources
            sources = sorted(set(
                event.get("source", "") for event in events
            ))
            
            # Update items if changed
            items = [
                self.source_filter.itemText(i)
                for i in range(self.source_filter.count())
            ]
            
            if ["All Sources"] + sources != items:
                self.source_filter.clear()
                self.source_filter.addItem("All Sources")
                self.source_filter.addItems(sources)
                
                # Restore selection
                index = self.source_filter.findText(current)
                if index >= 0:
                    self.source_filter.setCurrentIndex(index)
        except Exception as e:
            self.logger.error(f"Error updating source filter: {e}")
    
    def _handle_source_change(self, source: str):
        """Handle source filter change."""
        try:
            self.filter_source = source
            self._refresh_events()
        except Exception as e:
            self.logger.error(f"Error handling source change: {e}")
    
    def _handle_severity_change(self, severity: str):
        """Handle severity filter change."""
        try:
            self.filter_severity = severity
            self._refresh_events()
        except Exception as e:
            self.logger.error(f"Error handling severity change: {e}")
    
    def _handle_search_change(self, text: str):
        """Handle search text change."""
        try:
            self.search_text = text
            self._refresh_events()
        except Exception as e:
            self.logger.error(f"Error handling search change: {e}")
    
    def _handle_selection_change(self):
        """Handle event selection change."""
        try:
            selected_items = self.events_table.selectedItems()
            if not selected_items:
                self.selected_event = None
                self.details_text.clear()
                return
            
            row = selected_items[0].row()
            event_time = self.events_table.item(row, 0).text()
            event_source = self.events_table.item(row, 1).text()
            
            self.selected_event = self.feedback_engine.get_event(
                event_time, event_source
            )
            
            if self.selected_event:
                self._update_selected_event()
                self.event_selected.emit(self.selected_event)
        except Exception as e:
            self.logger.error(f"Error handling selection change: {e}")
    
    def _update_selected_event(self):
        """Update UI for selected event."""
        try:
            if not self.selected_event:
                return
            
            # Format event details
            details = (
                f"Time: {self.selected_event.get('timestamp')}\n"
                f"Source: {self.selected_event.get('source')}\n"
                f"Type: {self.selected_event.get('type')}\n"
                f"Severity: {self.selected_event.get('severity')}\n"
                f"Message: {self.selected_event.get('message')}\n\n"
                f"Data:\n{self.selected_event.get('data', {})}"
            )
            self.details_text.setText(details)
        except Exception as e:
            self.logger.error(f"Error updating selected event: {e}")
    
    def _show_context_menu(self, position):
        """Show context menu for events table."""
        try:
            if not self.selected_event:
                return
            
            menu = QMenu()
            
            # Add actions based on event type
            copy_action = menu.addAction(
                QIcon("assets/icons/copy.png"),
                "Copy Details"
            )
            copy_action.triggered.connect(self._copy_event_details)
            
            if self.selected_event.get("severity") == EventSeverity.ERROR:
                retry_action = menu.addAction(
                    QIcon("assets/icons/retry.png"),
                    "Retry Action"
                )
                retry_action.triggered.connect(self._retry_event_action)
            
            # Show menu
            menu.exec_(self.events_table.mapToGlobal(position))
        except Exception as e:
            self.logger.error(f"Error showing context menu: {e}")
    
    def _copy_event_details(self):
        """Copy selected event details to clipboard."""
        try:
            if not self.selected_event:
                return
            
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(self.details_text.toPlainText())
        except Exception as e:
            self.logger.error(f"Error copying event details: {e}")
            self._show_error("Failed to copy event details")
    
    def _retry_event_action(self):
        """Retry the action that caused the selected event."""
        try:
            if not self.selected_event:
                return
            
            self.event_action.emit("retry", self.selected_event)
        except Exception as e:
            self.logger.error(f"Error retrying event action: {e}")
            self._show_error("Failed to retry action")
    
    def _clear_events(self):
        """Clear all events."""
        try:
            self.feedback_engine.clear_events()
            self._refresh_events()
        except Exception as e:
            self.logger.error(f"Error clearing events: {e}")
            self._show_error("Failed to clear events")
    
    def _manual_refresh(self):
        """Handle manual refresh button click."""
        try:
            self._refresh_events()
        except Exception as e:
            self.logger.error(f"Error during manual refresh: {e}")
    
    def _handle_new_event(self, event_data: Dict):
        """Handle new event from feedback engine."""
        try:
            self._refresh_events()
        except Exception as e:
            self.logger.error(f"Error handling new event: {e}")
    
    def _show_error(self, message: str):
        """Show error message dialog."""
        QMessageBox.critical(self, "Error", message)
    
    def refresh_events(self):
        """Refresh events state."""
        try:
            self._refresh_events()
        except Exception as e:
            self.logger.error(f"Error refreshing events: {e}")

    def get_state(self) -> Dict:
        """Get current tab state for persistence."""
        try:
            return {
                "filter_source": self.filter_source,
                "filter_severity": self.filter_severity,
                "search_text": self.search_text,
                "selected_event_id": (
                    self.selected_event.get("id") if self.selected_event else None
                ),
                "table_scroll_position": self.events_table.verticalScrollBar().value(),
                "splitter_sizes": self.parent().findChild(QSplitter).sizes(),
                "unread_events": len(self.feedback_engine.get_unread_events())
            }
        except Exception as e:
            self.logger.error(f"Error getting tab state: {e}")
            return {}

    def restore_state(self, state: Dict):
        """Restore tab state from persisted data."""
        try:
            # Restore filters
            if state.get("filter_source"):
                index = self.source_filter.findText(state["filter_source"])
                if index >= 0:
                    self.source_filter.setCurrentIndex(index)
            
            if state.get("filter_severity"):
                index = self.severity_filter.findText(state["filter_severity"])
                if index >= 0:
                    self.severity_filter.setCurrentIndex(index)
            
            # Restore search
            if state.get("search_text"):
                self.search_box.setText(state["search_text"])
            
            # Restore selected event
            if state.get("selected_event_id"):
                event = self.feedback_engine.get_event_by_id(
                    state["selected_event_id"]
                )
                if event:
                    self.selected_event = event
                    self._update_selected_event()
            
            # Restore visual state
            if state.get("table_scroll_position"):
                self.events_table.verticalScrollBar().setValue(
                    state["table_scroll_position"]
                )
            
            if state.get("splitter_sizes"):
                splitter = self.parent().findChild(QSplitter)
                if splitter:
                    splitter.setSizes(state["splitter_sizes"])
            
            # Refresh display
            self._refresh_events()
            
            self.logger.info("Tab state restored successfully")
        except Exception as e:
            self.logger.error(f"Error restoring tab state: {e}")
            self._show_error("Failed to restore tab state")

    def prepare_for_shutdown(self):
        """Prepare tab for system shutdown."""
        try:
            # Stop refresh timer
            if self.refresh_timer:
                self.refresh_timer.stop()
            
            # Log final event counts
            event_stats = {
                "total_events": len(self.feedback_engine.get_events()),
                "unread_events": len(self.feedback_engine.get_unread_events()),
                "error_events": len([
                    e for e in self.feedback_engine.get_events()
                    if e.get("severity") == EventSeverity.ERROR
                ])
            }
            
            self.feedback_engine.log_event(
                "tab_shutdown",
                {
                    "source": "feedback_tab",
                    "severity": "info",
                    "data": {
                        "event_stats": event_stats,
                        "last_selected_event": (
                            self.selected_event.get("id")
                            if self.selected_event else None
                        )
                    }
                }
            )
            
            self.logger.info("Tab prepared for shutdown successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error preparing tab for shutdown: {e}")
            return False 