from PyQt5.QtWidgets import (
    QWidget,
    QListWidget,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QLineEdit,
    QFrame,
    QMenu,
    QAction,
)
from PyQt5.QtCore import Qt, QFile, QTextStream, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import frontmatter
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from ..services.devlog_harvester import DevlogHarvester, DevlogEntry


class DevlogHistoryPanel(QWidget):
    """Panel for viewing and managing generated devlogs."""

    # Signals
    devlog_selected = pyqtSignal(DevlogEntry)
    devlog_published = pyqtSignal(DevlogEntry, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Devlog History")
        self.harvester = DevlogHarvester()
        self.current_entry: Optional[DevlogEntry] = None

        # Initialize UI
        self._init_ui()

        # Load devlogs
        self.load_devlogs()

    def _init_ui(self):
        """Initialize the user interface."""
        # Main layout
        layout = QVBoxLayout()

        # Top controls
        controls = QHBoxLayout()

        # Filter controls
        self.template_filter = QComboBox()
        self.template_filter.addItems(
            ["All Templates", "Technical", "Victor", "Satirical"]
        )
        self.template_filter.currentTextChanged.connect(self.apply_filters)

        self.tech_filter = QLineEdit()
        self.tech_filter.setPlaceholderText("Filter by technology...")
        self.tech_filter.textChanged.connect(self.apply_filters)

        self.published_only = QPushButton("Published Only")
        self.published_only.setCheckable(True)
        self.published_only.clicked.connect(self.apply_filters)

        controls.addWidget(QLabel("Template:"))
        controls.addWidget(self.template_filter)
        controls.addWidget(QLabel("Technology:"))
        controls.addWidget(self.tech_filter)
        controls.addWidget(self.published_only)
        controls.addStretch()

        # Stats label
        self.stats_label = QLabel()
        controls.addWidget(self.stats_label)

        layout.addLayout(controls)

        # Splitter for list + preview
        splitter = QSplitter(Qt.Horizontal)

        # Left: List of devlogs
        list_frame = QFrame()
        list_frame.setFrameStyle(QFrame.StyledPanel)
        list_layout = QVBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Segoe UI", 10))
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)

        list_layout.addWidget(self.list_widget)
        list_frame.setLayout(list_layout)
        splitter.addWidget(list_frame)

        # Right: Preview panel
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.StyledPanel)
        preview_layout = QVBoxLayout()

        # Preview header
        preview_header = QHBoxLayout()
        self.preview_title = QLabel()
        self.preview_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        preview_header.addWidget(self.preview_title)

        # Action buttons
        self.publish_btn = QPushButton("Publish")
        self.publish_btn.clicked.connect(self._publish_devlog)
        preview_header.addWidget(self.publish_btn)

        preview_layout.addLayout(preview_header)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Segoe UI", 10))
        preview_layout.addWidget(self.preview)

        preview_frame.setLayout(preview_layout)
        splitter.addWidget(preview_frame)

        # Set splitter sizes
        splitter.setSizes([200, 600])

        layout.addWidget(splitter)
        self.setLayout(layout)

        # Connect selection
        self.list_widget.currentRowChanged.connect(self.show_devlog)

    def _show_context_menu(self, pos):
        """Show context menu for devlog actions."""
        if not self.current_entry:
            return

        menu = QMenu()

        # View actions
        view_action = QAction("View in Browser", self)
        view_action.triggered.connect(lambda: self._view_in_browser())
        menu.addAction(view_action)

        # Edit actions
        edit_action = QAction("Edit Content", self)
        edit_action.triggered.connect(lambda: self._edit_devlog())
        menu.addAction(edit_action)

        # Publishing actions
        if not self.current_entry.published:
            publish_action = QAction("Publish...", self)
            publish_action.triggered.connect(lambda: self._publish_devlog())
            menu.addAction(publish_action)

        menu.exec_(self.list_widget.mapToGlobal(pos))

    def _view_in_browser(self):
        """Open the devlog in the default browser."""
        if self.current_entry:
            path = Path("output/devlogs") / f"devlog_{self.current_entry.title}.md"
            if path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _edit_devlog(self):
        """Open the devlog in the default editor."""
        if self.current_entry:
            path = Path("output/devlogs") / f"devlog_{self.current_entry.title}.md"
            if path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _publish_devlog(self):
        """Show publish dialog and handle publishing."""
        if not self.current_entry:
            return

        # TODO: Show platform selection dialog
        platforms = ["WordPress", "Medium", "Dev.to"]  # Example platforms
        self.devlog_published.emit(self.current_entry, platforms)

    def load_devlogs(self):
        """Load devlogs from the harvester."""
        self.list_widget.clear()
        self.devlog_entries = self.harvester.get_history()

        for entry in self.devlog_entries:
            # Format the list item
            date_str = entry.generated_at.strftime("%Y-%m-%d %H:%M")
            status = "✓" if entry.published else "○"
            label = f"{status} {date_str} — {entry.title}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, entry)
            self.list_widget.addItem(item)

        self._update_stats()

    def show_devlog(self, index: int):
        """Display the selected devlog content."""
        if 0 <= index < len(self.devlog_entries):
            self.current_entry = self.devlog_entries[index]

            # Update preview
            self.preview_title.setText(self.current_entry.title)
            self.preview.setPlainText(self.current_entry.content)

            # Update publish button
            self.publish_btn.setEnabled(not self.current_entry.published)
            self.publish_btn.setText(
                "Republish" if self.current_entry.published else "Publish"
            )

            # Emit signal
            self.devlog_selected.emit(self.current_entry)
        else:
            self.current_entry = None
            self.preview_title.clear()
            self.preview.clear()
            self.publish_btn.setEnabled(False)

    def apply_filters(self):
        """Apply filters to the devlog list."""
        template = self.template_filter.currentText()
        tech = self.tech_filter.text().strip()
        published = self.published_only.isChecked()

        # Get filtered entries
        entries = self.harvester.get_history(
            published_only=published,
            template=template if template != "All Templates" else None,
            technology=tech if tech else None,
        )

        # Update list
        self.list_widget.clear()
        self.devlog_entries = entries

        for entry in entries:
            date_str = entry.generated_at.strftime("%Y-%m-%d %H:%M")
            status = "✓" if entry.published else "○"
            label = f"{status} {date_str} — {entry.title}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, entry)
            self.list_widget.addItem(item)

        self._update_stats()

    def _update_stats(self):
        """Update the statistics label."""
        stats = self.harvester.get_stats()
        self.stats_label.setText(
            f"Total: {stats['total_devlogs']} | "
            f"Published: {stats['published_devlogs']} | "
            f"Templates: {', '.join(f'{k}: {v}' for k, v in stats['templates_used'].items())}"
        )
