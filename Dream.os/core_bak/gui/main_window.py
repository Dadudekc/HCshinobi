"""Dream.OS Main Application Window."""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import json
import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QApplication,
    QStatusBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QCloseEvent

from core.task_manager import TaskManager
from core.feedback_engine import FeedbackEngine
from core.gui.tab_manager import DreamOSTabManager
from core.gui.tab_system_shutdown import TabSystemShutdownManager
from core.utils.logger import get_logger
from core.gui.theme import DreamTheme # Import the theme

# Get logger for the main window component
logger = get_logger(__name__, component="MainWindow")

class DreamOSMainWindow(QMainWindow):
    """Main window for Dream.OS application."""

    def __init__(self):
        super().__init__()
        # Get logger specific to this instance/module, but still part of MainWindow component
        self.logger = get_logger(__name__, component="MainWindow")
        self.state_file = Path("agent_directory") / "tab_states.json" # Define state file path

        # State flags for UI indicators
        self.shutdown_in_progress = False
        self.is_loading_state = False
        self.is_saving_state = False
        self.last_error_message = None

        # Core components
        self.task_manager = TaskManager()
        self.feedback_engine = FeedbackEngine()
        
        # Initialize UI
        self._setup_ui()
        self._setup_status_bar()
        self._setup_shutdown_manager()
        
        # Load previous state
        self._load_state() # Call state loading method
        
        # Start auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save_state)
        self.auto_save_timer.start(300000)  # Save every 5 minutes
        
        self.logger.info("Main window initialized successfully")

    def _setup_ui(self):
        """Setup the main window UI."""
        try:
            self.setWindowTitle("Dream.OS")
            self.setMinimumSize(1024, 768)

            # Central widget
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout()
            central.setLayout(layout)

            # Tab manager
            self.tab_manager = DreamOSTabManager(
                self.task_manager,
                self.feedback_engine
            )
            layout.addWidget(self.tab_manager)

            # Control bar
            control_layout = QHBoxLayout()
            
            # System status
            self.status_label = QLabel("System Status: Ready")
            control_layout.addWidget(self.status_label)
            
            control_layout.addStretch()
            
            # Action buttons
            self.save_btn = QPushButton("Save State")
            self.save_btn.setIcon(QIcon("assets/icons/save.png"))
            self.save_btn.clicked.connect(self._manual_save_state)
            
            self.shutdown_btn = QPushButton("Shutdown")
            self.shutdown_btn.setIcon(QIcon("assets/icons/shutdown.png"))
            self.shutdown_btn.clicked.connect(self._initiate_shutdown)
            
            control_layout.addWidget(self.save_btn)
            control_layout.addWidget(self.shutdown_btn)
            
            layout.addLayout(control_layout)

        except Exception as e:
            self.logger.error(f"Error setting up UI: {e}")
            QMessageBox.critical(self, "Error", "Failed to initialize UI")

    def _setup_status_bar(self):
        """Setup the status bar."""
        try:
            status_bar = QStatusBar()
            self.setStatusBar(status_bar)
            
            # Add permanent widgets
            self.task_count_label = QLabel("Tasks: 0")
            status_bar.addPermanentWidget(self.task_count_label)
            
            self.event_count_label = QLabel("Events: 0")
            status_bar.addPermanentWidget(self.event_count_label)
            
            # Update timer
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self._update_status)
            self.status_timer.start(1000)  # Update every second

        except Exception as e:
            self.logger.error(f"Error setting up status bar: {e}")

    def _setup_shutdown_manager(self):
        """Setup the shutdown manager."""
        try:
            self.shutdown_manager = TabSystemShutdownManager(
                self.feedback_engine,
                "agent_directory"
            )
            
            # Connect shutdown signal
            self.shutdown_manager.shutdown_complete.connect(
                self._handle_shutdown_complete
            )

        except Exception as e:
            self.logger.error(f"Error setting up shutdown manager: {e}")
            QMessageBox.critical(self, "Error", "Failed to initialize shutdown manager")

    def _update_status(self):
        """Update status bar information and main status label based on state."""
        try:
            # Update task count
            task_count = len(self.task_manager.get_tasks())
            self.task_count_label.setText(f"Tasks: {task_count}")
            
            # Update event count
            event_count = len(self.feedback_engine.get_events())
            self.event_count_label.setText(f"Events: {event_count}")
            
            # Update main status label text and color
            status_text = "System Status: Ready"
            status_color = "" # Default text color

            if self.shutdown_in_progress:
                status_text = "System Status: Shutting Down..."
                status_color = DreamTheme.WARNING # Use warning color for shutdown
            elif self.is_loading_state:
                status_text = "System Status: Loading State..."
                status_color = DreamTheme.INFO # Use info color for loading
            elif self.is_saving_state:
                status_text = "System Status: Saving State..."
                status_color = DreamTheme.INFO # Use info color for saving
            elif self.last_error_message:
                status_text = f"System Status: Error - {self.last_error_message[:50]}..."
                status_color = DreamTheme.ERROR # Use error color

            self.status_label.setText(status_text)
            if status_color:
                self.status_label.setStyleSheet(f"color: {status_color};")
            else:
                self.status_label.setStyleSheet("") # Reset style

            # Show temporary messages in the status bar (e.g., for auto-save)
            # This is handled by calls like self.statusBar().showMessage()

        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
            # Avoid setting error state within the status update itself to prevent loops

    def set_error_state(self, message: str):
        """Sets the error state and triggers a status update."""
        self.last_error_message = message
        self.shutdown_in_progress = False # Clear other states if error occurs
        self.is_loading_state = False
        self.is_saving_state = False
        self._update_status() # Update UI immediately

    def clear_error_state(self):
        """Clears the error state and updates status."""
        if self.last_error_message:
            self.last_error_message = None
            self._update_status()

    def _auto_save_state(self):
        """Automatically save system state."""
        if self.is_saving_state: # Avoid concurrent saves
            return
        self.is_saving_state = True
        self.clear_error_state()
        self._update_status()
        QApplication.processEvents() # Update UI immediately
        try:
            self._save_state() # Call the core save logic
            self.statusBar().showMessage("Auto-saved system state", 3000)
        except Exception as e:
            self.logger.error(f"Error during auto-save: {e}")
            self.set_error_state("Auto-save failed") # Set error state
        finally:
            self.is_saving_state = False
            self._update_status() # Update status after operation completes or fails

    def _manual_save_state(self):
        """Handle manual save button click."""
        if self.is_saving_state:
            QMessageBox.warning(self, "Busy", "Already saving state.")
            return
        self.is_saving_state = True
        self.clear_error_state()
        self._update_status()
        QApplication.processEvents()
        try:
            self._save_state() # Call the core save logic
            QMessageBox.information(self, "Success", "System state saved successfully")
        except Exception as e:
            self.logger.error(f"Error during manual save: {e}")
            self.set_error_state("Manual save failed") # Set error state
            QMessageBox.critical(self, "Error", f"Failed to save system state: {e}")
        finally:
            self.is_saving_state = False
            self._update_status() # Update status after operation

    def _load_state(self):
        """Load persisted tab states from file."""
        try:
            if not self.state_file.exists():
                self.logger.info("No previous state file found. Starting fresh.")
                return

            self.logger.info(f"Loading previous state from {self.state_file}")
            with open(self.state_file, "r", encoding='utf-8') as f:
                try:
                    loaded_states = json.load(f)
                except json.JSONDecodeError as json_err:
                    self.logger.error(f"Error decoding state file {self.state_file}: {json_err}")
                    QMessageBox.warning(self, "State Load Error", f"Could not load previous state: Invalid format in {self.state_file.name}")
                    return # Don't attempt to restore from corrupt file

            if not isinstance(loaded_states, dict):
                self.logger.error(f"Loaded state from {self.state_file} is not a dictionary.")
                QMessageBox.warning(self, "State Load Error", f"Could not load previous state: Invalid structure in {self.state_file.name}")
                return

            restored_count = 0
            failed_tabs = []
            for tab_name, state in loaded_states.items():
                tab_widget = None
                # Find the tab widget by its stored name (which should match the keys used in saving)
                for i in range(self.tab_manager.count()):
                    current_tab_name = self.tab_manager.tabText(i).lower().replace(" ", "_")
                    if current_tab_name == tab_name:
                        tab_widget = self.tab_manager.widget(i)
                        break

                if tab_widget and hasattr(tab_widget, 'restore_state'):
                    try:
                        self.logger.debug(f"Restoring state for tab: {tab_name}")
                        tab_widget.restore_state(state)
                        restored_count += 1
                    except Exception as e:
                        self.logger.error(f"Error restoring state for tab '{tab_name}': {e}", exc_info=True)
                        failed_tabs.append(tab_name)
                elif tab_widget:
                    self.logger.warning(f"Tab '{tab_name}' found but has no 'restore_state' method.")
                else:
                    self.logger.warning(f"Tab '{tab_name}' from state file not found in current UI.")

            if restored_count > 0:
                 self.statusBar().showMessage(f"Restored state for {restored_count} tabs.", 5000)
                 self.logger.info(f"Successfully restored state for {restored_count} tabs.")
            if failed_tabs:
                self.logger.error(f"Failed to restore state for tabs: {', '.join(failed_tabs)}")
                QMessageBox.warning(self, "State Restore Warning", f"Could not restore state for some tabs: {', '.join(failed_tabs)}")

        except FileNotFoundError:
             self.logger.info("State file not found, nothing to load.")
        except Exception as e:
            self.logger.critical(f"Critical error loading state: {e}", exc_info=True)
            QMessageBox.critical(self, "State Load Error", "A critical error occurred while loading the previous state.")

    def _save_state(self):
        """Save the current system state."""
        try:
            # Get states from all tabs
            tab_states = {}
            for i in range(self.tab_manager.count()):
                tab = self.tab_manager.widget(i)
                if hasattr(tab, 'get_state'):
                    tab_name = self.tab_manager.tabText(i).lower().replace(" ", "_")
                    try:
                         state = tab.get_state()
                         if state is not None:
                             tab_states[tab_name] = state
                         else:
                            self.logger.warning(f"Tab '{tab_name}' returned None state during save.")
                    except Exception as e:
                        self.logger.error(f"Error getting state from tab '{tab_name}' during save: {e}", exc_info=True)
                        # Decide if we should skip this tab or abort saving
                        # For now, log and skip.

            if not tab_states:
                 self.logger.warning("No tab states collected to save.")
                 return # Don't write empty file

            # Save to file
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, "w", encoding='utf-8') as f:
                json.dump(tab_states, f, indent=2, default=str) # Use default=str for complex types

            self.feedback_engine.log_event(
                "state_saved",
                {
                    "source": "main_window",
                    "severity": "info",
                    "data": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "tabs_saved": list(tab_states.keys())
                    }
                }
            )

        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
            raise

    def _initiate_shutdown(self):
        """Handle shutdown button click."""
        try:
            # Confirm shutdown
            reply = QMessageBox.question(
                self,
                "Confirm Shutdown",
                "Are you sure you want to shutdown Dream.OS?\nAll tabs will be closed and state will be persisted.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Run pre-shutdown checks
                if self.shutdown_manager._log_pre_shutdown_check():
                    self.shutdown_in_progress = True
                    self._update_status()
                    
                    # Disable UI
                    self.setEnabled(False)
                    QApplication.processEvents()
                    
                    # Get tab references
                    tabs = {
                        self.tab_manager.tabText(i).lower().replace(" ", "_"):
                        self.tab_manager.widget(i)
                        for i in range(self.tab_manager.count())
                    }
                    
                    # Initiate shutdown
                    self.shutdown_manager.initiate_shutdown(tabs)
                else:
                    QMessageBox.critical(
                        self,
                        "Shutdown Blocked",
                        "Pre-shutdown checks failed. Please check the feedback tab for details."
                    )

        except Exception as e:
            self.logger.error(f"Error initiating shutdown: {e}")
            QMessageBox.critical(self, "Error", "Failed to initiate shutdown")

    def _handle_shutdown_complete(self):
        """Handle the shutdown complete signal from the manager."""
        try:
            self.logger.info("TabSystemShutdownManager reported completion. Proceeding with application exit.")
            # Re-enable UI elements (optional, depends on whether shutdown could fail and require interaction)
            # self.setEnabled(True)
            # QApplication.processEvents()

            # Signal the application to close
            # Use QTimer to ensure it happens after the current event loop cycle
            QTimer.singleShot(0, self.close) 

        except Exception as e:
            self.logger.critical(f"Error handling shutdown completion: {e}")
            # Fallback: Force close if handling fails
            QApplication.instance().quit()

    def closeEvent(self, event: QCloseEvent):
        """Handle the main window close event."""
        try:
            self.logger.info("Close event triggered for main window.")
            
            # Check if shutdown is already in progress
            if hasattr(self, 'shutdown_in_progress') and self.shutdown_in_progress:
                self.logger.info("Shutdown already in progress, accepting close event.")
                event.accept()
                return

            # Initiate shutdown if not already started
            self.logger.info("Initiating shutdown sequence from close event.")
            self._initiate_shutdown() # This will trigger the shutdown manager
            
            # Ignore the immediate close event; wait for shutdown_complete signal
            # unless initiate_shutdown failed immediately (e.g., pre-checks)
            if not (hasattr(self, 'shutdown_in_progress') and self.shutdown_in_progress):
                self.logger.warning("Shutdown initiation failed or was cancelled, accepting close event.")
                event.accept() # Allow closing if shutdown didn't start
            else:
                self.logger.info("Ignoring initial close event, waiting for shutdown manager signal.")
                event.ignore()

        except Exception as e:
            self.logger.error(f"Error during closeEvent: {e}")
            event.accept() # Ensure window closes on error 