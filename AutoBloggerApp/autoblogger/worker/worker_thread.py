# autoblogger/worker/worker_thread.py

from PyQt5.QtCore import QThread, pyqtSignal
import logging
from datetime import datetime
import os
from pathlib import Path
from autoblogger.services.blog_generator import BlogGenerator
from autoblogger.scrapers.chatgpt import ChatGPTScraper
from autoblogger.services.devlog_service import DevlogService


class WorkerThread(QThread):
    """Worker thread for generating devlogs."""

    # Signals
    progress = pyqtSignal(int)  # Progress percentage
    log = pyqtSignal(str)  # Log messages
    finished = pyqtSignal(str)  # Generated devlog content

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.context = None
        self.scraper = None
        self.devlog_service = None

    def set_params(self, context: dict):
        """Set the generation parameters."""
        self.context = context

    def run(self):
        """Run the devlog generation process."""
        try:
            # Initialize services
            self.scraper = ChatGPTScraper()
            self.devlog_service = DevlogService(self.scraper)

            # Log start
            self.log.emit("Starting devlog generation...")
            self.progress.emit(10)

            # Generate devlog
            self.log.emit("Generating devlog content...")
            devlog = self.devlog_service.generate_devlog(self.context)
            self.progress.emit(90)

            # Complete
            self.log.emit("Devlog generation complete!")
            self.progress.emit(100)

            # Emit result
            self.finished.emit(devlog)

        except Exception as e:
            self.logger.error(f"Error in worker thread: {str(e)}")
            self.log.emit(f"Error: {str(e)}")
            self.finished.emit(None)
