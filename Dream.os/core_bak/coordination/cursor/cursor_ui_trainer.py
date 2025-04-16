"""UI element trainer for Cursor instances."""

import sys
import json
import datetime
from pathlib import Path
from typing import Optional, Dict

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, 
    QHBoxLayout, QComboBox, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer
from PyQt5.QtGui import QPixmap, QScreen, QPainter, QColor

from cursor_window_controller import CursorWindowController, WindowWrapper

class CursorUITrainer(QWidget):
    """Training UI for capturing Cursor interface elements."""
    
    BUTTON_TYPES = {
        "resume_button": "Resume Generation",
        "accept_button": "Accept Changes",
        "accept_all_button": "Accept All Changes",
        "copy_message_button": "Copy Message",
        "chat_input": "Chat Input Area",
        "send_button": "Send Message",
        "stop_button": "Stop Generation"
    }
    
    def __init__(self):
        super().__init__()
        self.window_controller = CursorWindowController()
        self.current_window: Optional[WindowWrapper] = None
        self.setup_ui()
        self.setup_data_dirs()
        
    def setup_data_dirs(self):
        """Initialize directory structure for training data."""
        self.output_dir = Path("./cursor_training_data")
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for each window
        for i in range(1, self.window_controller.MAX_INSTANCES + 1):
            window_dir = self.output_dir / f"CURSOR-{i}"
            window_dir.mkdir(exist_ok=True)
            (window_dir / "cropped").mkdir(exist_ok=True)
            (window_dir / "full_screens").mkdir(exist_ok=True)
            
            # Initialize metadata file
            metadata_file = window_dir / "labels.json"
            if not metadata_file.exists():
                metadata_file.write_text("[]")
                
    def setup_ui(self):
        """Set up the trainer interface."""
        self.setWindowTitle("Cursor UI Element Trainer")
        self.setGeometry(100, 100, 400, 600)
        
        layout = QVBoxLayout()
        
        # Window selector
        window_layout = QHBoxLayout()
        self.window_label = QLabel("Select Cursor Window:", self)
        self.window_combo = QComboBox(self)
        self.refresh_btn = QPushButton("🔄", self)
        self.refresh_btn.setFixedWidth(30)
        window_layout.addWidget(self.window_label)
        window_layout.addWidget(self.window_combo)
        window_layout.addWidget(self.refresh_btn)
        layout.addLayout(window_layout)
        
        # Status label
        self.status_label = QLabel("Select a window and UI element to capture", self)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; }")
        layout.addWidget(self.status_label)
        
        # Element capture buttons
        for key, label in self.BUTTON_TYPES.items():
            btn = QPushButton(f"Capture {label}", self)
            btn.clicked.connect(lambda checked, k=key: self.prepare_capture(k))
            layout.addWidget(btn)
            
        # Preview area
        self.preview_label = QLabel(self)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet("QLabel { background-color: #e0e0e0; }")
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)
        
        self.setLayout(layout)
        
        # Connect signals
        self.refresh_btn.clicked.connect(self.refresh_windows)
        self.window_combo.currentIndexChanged.connect(self.on_window_selected)
        
        # Initial window scan
        self.refresh_windows()
        
    def refresh_windows(self):
        """Scan for Cursor windows and update the combo box."""
        self.window_combo.clear()
        windows = self.window_controller.detect_all_instances()
        
        for window in windows:
            self.window_combo.addItem(f"{window.id}: {window.title}", window)
            
        if windows:
            self.status_label.setText("Select a UI element to capture")
        else:
            self.status_label.setText("No Cursor windows detected! Please open Cursor.")
            
    def on_window_selected(self, index):
        """Handle window selection."""
        if index >= 0:
            self.current_window = self.window_combo.itemData(index)
            self.status_label.setText(f"Selected {self.current_window.id}")
            
            # Activate the window
            self.window_controller.activate_window(self.current_window)
        else:
            self.current_window = None
            
    def prepare_capture(self, element_type: str):
        """Prepare to capture a UI element."""
        if not self.current_window:
            QMessageBox.warning(self, "Error", "Please select a Cursor window first!")
            return
            
        # Minimize our window temporarily
        self.setWindowState(Qt.WindowMinimized)
        
        # Activate target window
        self.window_controller.activate_window(self.current_window)
        
        # Schedule capture
        self.status_label.setText(f"Capturing {self.BUTTON_TYPES[element_type]} in 3 seconds...")
        QTimer.singleShot(3000, lambda: self.capture_element(element_type))
        
    def capture_element(self, element_type: str):
        """Capture screenshots and save metadata."""
        if not self.current_window:
            return
            
        # Get window-specific paths
        window_dir = self.output_dir / self.current_window.id
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Capture full screen
        screen = QApplication.instance().primaryScreen()
        full = screen.grabWindow(0)
        full_path = window_dir / "full_screens" / f"{element_type}_{timestamp}.png"
        full.save(str(full_path))
        
        # Get window geometry for cropping
        geo = self.current_window.geometry
        window_rect = QRect(geo['x'], geo['y'], geo['width'], geo['height'])
        
        # Crop to window area
        cropped = full.copy(window_rect)
        crop_path = window_dir / "cropped" / f"{element_type}_{timestamp}.png"
        cropped.save(str(crop_path))
        
        # Save metadata
        metadata_file = window_dir / "labels.json"
        metadata = json.loads(metadata_file.read_text())
        metadata.append({
            "timestamp": timestamp,
            "element_type": element_type,
            "element_name": self.BUTTON_TYPES[element_type],
            "window_id": self.current_window.id,
            "window_title": self.current_window.title,
            "full_image": str(full_path),
            "cropped_image": str(crop_path),
            "window_geometry": self.current_window.geometry,
            "screen_size": [full.width(), full.height()]
        })
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        # Update preview
        scaled_preview = cropped.scaled(
            self.preview_label.width(), 
            self.preview_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled_preview)
        
        # Restore window and update status
        self.setWindowState(Qt.WindowActive)
        self.status_label.setText(
            f"✅ Captured {self.BUTTON_TYPES[element_type]} "
            f"for {self.current_window.id} at {timestamp}"
        )

def main():
    app = QApplication(sys.argv)
    trainer = CursorUITrainer()
    trainer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 