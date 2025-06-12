#!/usr/bin/env python3
"""
AutoBlogger Beta Verification GUI

A modern PyQt5 interface for the AutoBlogger beta verification tool.
Provides real-time progress updates, interactive result viewing,
and the ability to export reports in various formats.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QFrame,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor

from verify_beta import AutoBloggerVerifier, CheckResult


class VerificationWorker(QThread):
    """Worker thread for running verification checks."""

    progress = pyqtSignal(int)
    result = pyqtSignal(str, bool, str)
    finished = pyqtSignal(dict)

    def run(self):
        """Run the verification process."""
        try:
            verifier = AutoBloggerVerifier()
            results = verifier.run_all()
            self.finished.emit(results)
        except Exception as e:
            self.result.emit("Error", False, str(e))


class ResultTree(QTreeWidget):
    """Custom tree widget for displaying verification results."""

    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Check", "Status", "Details"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 100)

    def add_result(self, name: str, status: bool, details: str):
        """Add a verification result to the tree."""
        item = QTreeWidgetItem(self)
        item.setText(0, name)
        item.setText(1, "✓" if status else "✗")
        item.setText(2, details)

        # Set color based on status
        color = Qt.green if status else Qt.red
        item.setForeground(1, color)


class BetaVerificationGUI(QMainWindow):
    """Main window for the beta verification GUI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoBlogger Beta Verification")
        self.setMinimumSize(800, 600)

        # Initialize UI
        self._init_ui()

        # Store results
        self.results: Dict[str, CheckResult] = {}

    def _init_ui(self):
        """Initialize the user interface."""
        # Create central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Create header
        header = QLabel("AutoBlogger Beta Verification")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Create progress section
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)

        # Create splitter for results and details
        splitter = QSplitter(Qt.Vertical)

        # Create results tree
        self.results_tree = ResultTree()
        self.results_tree.itemClicked.connect(self.show_details)
        splitter.addWidget(self.results_tree)

        # Create details panel
        details_frame = QFrame()
        details_frame.setFrameStyle(QFrame.StyledPanel)
        details_layout = QVBoxLayout()

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)

        details_frame.setLayout(details_layout)
        splitter.addWidget(details_frame)

        layout.addWidget(splitter)

        # Create button panel
        button_layout = QHBoxLayout()

        self.verify_button = QPushButton("Run Verification")
        self.verify_button.clicked.connect(self.run_verification)
        button_layout.addWidget(self.verify_button)

        self.export_button = QPushButton("Export Report")
        self.export_button.clicked.connect(self.export_report)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)

        layout.addLayout(button_layout)

    def run_verification(self):
        """Run the verification process."""
        self.verify_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_tree.clear()
        self.results.clear()

        # Create and start worker
        self.worker = VerificationWorker()
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(self.add_result)
        self.worker.finished.connect(self.verification_finished)
        self.worker.start()

    def update_progress(self, value: int):
        """Update the progress bar."""
        self.progress_bar.setValue(value)
        self.status_label.setText(f"Running: {value}%")

    def add_result(self, name: str, status: bool, details: str):
        """Add a verification result."""
        self.results[name] = CheckResult(name, status, details, [])
        self.results_tree.add_result(name, status, details)

    def verification_finished(self, results: dict):
        """Handle verification completion."""
        self.verify_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText("Verification complete")

        # Show summary
        total = len(results)
        passed = sum(1 for r in results.values() if r["status"])
        failed = total - passed

        QMessageBox.information(
            self,
            "Verification Complete",
            f"Verification completed:\n"
            f"Total checks: {total}\n"
            f"Passed: {passed}\n"
            f"Failed: {failed}",
        )

    def show_details(self, item: QTreeWidgetItem):
        """Show details for the selected result."""
        details = item.text(2)
        self.details_text.setText(details)

    def export_report(self):
        """Export the verification report."""
        if not self.results:
            return

        verifier = AutoBloggerVerifier()
        verifier.results = list(self.results.values())

        try:
            # Get save location
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Report",
                str(Path.home() / "autoblogger_verification_report.json"),
                "JSON Files (*.json)",
            )

            if not path:
                return

            # Collect results
            results = {}
            for i in range(self.results_tree.topLevelItemCount()):
                item = self.results_tree.topLevelItem(i)
                results[item.text(0)] = {
                    "status": item.text(1) == "✓",
                    "details": item.text(2),
                }

            # Save report
            with open(path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

            QMessageBox.information(self, "Success", f"Report exported to: {path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export report: {str(e)}")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look

    window = BetaVerificationGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
