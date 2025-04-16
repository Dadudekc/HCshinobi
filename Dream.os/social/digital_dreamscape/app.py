"""
Digital Dreamscape Chronicles - A GUI application for managing ChatGPT conversations.
"""
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QSplitter,
    QTextEdit, QMessageBox, QProgressBar, QComboBox, QCheckBox,
    QFileDialog, QStatusBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap

from utils.chatgpt_scraper import ChatGPTScraper

class ChatScraperWorker(QThread):
    """Worker thread for running the ChatGPT scraper."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, model: str = ""):
        super().__init__()
        self.model = model
        
    def run(self):
        try:
            with ChatGPTScraper() as scraper:
                # Emit 25% progress for initialization
                self.progress.emit(25)
                
                success = scraper.run_scraper(
                    model_append=f"?model={self.model}" if self.model else "",
                    output_file="temp_chats.json"
                )
                
                if not success:
                    self.error.emit("Failed to scrape chats")
                    return
                
                # Emit 75% progress for successful scraping
                self.progress.emit(75)
                
                # Load the scraped chats
                with open("temp_chats.json", "r") as f:
                    chats = json.load(f)
                
                # Cleanup temporary file
                os.remove("temp_chats.json")
                
                # Emit 100% progress and results
                self.progress.emit(100)
                self.finished.emit(chats)
                
        except Exception as e:
            self.error.emit(str(e))

class DigitalDreamscapeWindow(QMainWindow):
    """Main window for the Digital Dreamscape Chronicles application."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Dreamscape Chronicles")
        self.setMinimumSize(1200, 800)
        
        # Initialize UI components
        self.init_ui()
        
        # Initialize data
        self.chats = []
        self.selected_chats = set()
        
    def init_ui(self):
        """Initialize the user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create header
        header_layout = QHBoxLayout()
        title_label = QLabel("Digital Dreamscape Chronicles")
        title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        # Add model selector
        self.model_selector = QComboBox()
        self.model_selector.addItems(["", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"])
        self.model_selector.setCurrentText("")
        header_layout.addWidget(QLabel("Model:"))
        header_layout.addWidget(self.model_selector)
        
        # Add refresh button
        refresh_btn = QPushButton("Refresh Chats")
        refresh_btn.clicked.connect(self.refresh_chats)
        header_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        # Create splitter for chat list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Chat list panel
        chat_panel = QWidget()
        chat_layout = QVBoxLayout(chat_panel)
        
        # Add chat list
        self.chat_list = QListWidget()
        self.chat_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.chat_list.itemSelectionChanged.connect(self.update_selection)
        chat_layout.addWidget(self.chat_list)
        
        # Add selection controls
        selection_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_chats)
        clear_selection_btn = QPushButton("Clear Selection")
        clear_selection_btn.clicked.connect(self.clear_selection)
        selection_layout.addWidget(select_all_btn)
        selection_layout.addWidget(clear_selection_btn)
        chat_layout.addLayout(selection_layout)
        
        splitter.addWidget(chat_panel)
        
        # Preview panel
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        
        preview_label = QLabel("Preview")
        preview_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        preview_layout.addWidget(preview_label)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        splitter.addWidget(preview_panel)
        
        main_layout.addWidget(splitter)
        
        # Add export controls
        export_layout = QHBoxLayout()
        export_selected_btn = QPushButton("Export Selected")
        export_selected_btn.clicked.connect(self.export_selected)
        export_layout.addWidget(export_selected_btn)
        
        self.include_content_cb = QCheckBox("Include Chat Content")
        export_layout.addWidget(self.include_content_cb)
        
        main_layout.addLayout(export_layout)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
    def refresh_chats(self):
        """Refresh the chat list using the scraper."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Create and start worker thread
        self.worker = ChatScraperWorker(self.model_selector.currentText())
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.update_chat_list)
        self.worker.error.connect(self.show_error)
        self.worker.start()
        
    def update_progress(self, value: int):
        """Update the progress bar."""
        self.progress_bar.setValue(value)
        
    def update_chat_list(self, chats: List[Dict]):
        """Update the chat list with new data."""
        self.chats = chats
        self.chat_list.clear()
        
        for chat in chats:
            item = QListWidgetItem(chat["title"])
            item.setData(Qt.ItemDataRole.UserRole, chat)
            self.chat_list.addItem(item)
            
        self.status_bar.showMessage(f"Loaded {len(chats)} chats")
        self.progress_bar.setVisible(False)
        
    def show_error(self, message: str):
        """Show error message."""
        QMessageBox.critical(self, "Error", message)
        self.progress_bar.setVisible(False)
        
    def update_selection(self):
        """Update the preview based on selection."""
        selected_items = self.chat_list.selectedItems()
        self.selected_chats = {item.data(Qt.ItemDataRole.UserRole)["url"] for item in selected_items}
        
        preview_text = f"Selected {len(selected_items)} chats:\n\n"
        for item in selected_items:
            chat = item.data(Qt.ItemDataRole.UserRole)
            preview_text += f"• {chat['title']}\n"
            preview_text += f"  URL: {chat['url']}\n"
            if chat.get('timestamp'):
                preview_text += f"  Timestamp: {chat['timestamp']}\n"
            preview_text += "\n"
            
        self.preview_text.setText(preview_text)
        
    def select_all_chats(self):
        """Select all chats in the list."""
        self.chat_list.selectAll()
        
    def clear_selection(self):
        """Clear the current selection."""
        self.chat_list.clearSelection()
        
    def export_selected(self):
        """Export selected chats."""
        if not self.selected_chats:
            QMessageBox.warning(self, "Warning", "No chats selected")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Chats",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        selected_data = [
            chat for chat in self.chats
            if chat["url"] in self.selected_chats
        ]
        
        try:
            with open(file_path, 'w') as f:
                json.dump(selected_data, f, indent=2)
            QMessageBox.information(
                self,
                "Success",
                f"Successfully exported {len(selected_data)} chats to {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = DigitalDreamscapeWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 