# autoblogger/ui/main_window.py

from autoblogger.ui.dialogs import SetupWizardDialog, SettingsDialog
from autoblogger.services.blog_generator import generate_blog
from autoblogger.services.vector_db import VectorDB
from autoblogger.services.wordpress_client import WordPressClient
from autoblogger.worker.worker_thread import WorkerThread
from pathlib import Path
import sys
import configparser
from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QProgressBar,
    QTextEdit,
    QDialog,
    QMessageBox,
    QTabWidget,
    QLabel,
    QComboBox,
    QSpinBox,
    QCalendarWidget,
    QSplitter,
    QFrame,
    QToolBar,
    QStatusBar,
    QAction,
    QLineEdit,
    QFileDialog,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
import logging
from datetime import datetime
from autoblogger.services.analytics import AnalyticsService
from autoblogger.ui.charts import AnalyticsChart, DistributionChart, EngagementPieChart
from autoblogger.services.mistral_client import MistralClient
from autoblogger.services.blog_generator import BlogGenerator
import os
from typing import Dict, List
from .devlog_history_panel import DevlogHistoryPanel
from ..services.devlog_harvester import DevlogHarvester, DevlogEntry


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("AutoBloggerApp")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize services
        self.init_services()

        # Setup UI
        self.init_ui()

        # Initialize other attributes
        self.latest_output_path = ""

    def init_services(self):
        """Initialize core services and configuration."""
        self.config = configparser.ConfigParser()
        config_path = Path(__file__).resolve().parent.parent / "config" / "config.ini"

        if not config_path.exists():
            self.launch_setup_wizard(config_path)
        else:
            self.config.read(str(config_path))
            self.vector_db = VectorDB()
            self.wordpress_client = WordPressClient(self.config)

    def init_ui(self):
        """Initialize and setup the main UI components."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create toolbar
        self.create_toolbar()

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Create main content area with tabs
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Add tabs
        self.setup_dashboard_tab()
        self.setup_devlog_tab()
        self.setup_analytics_tab()
        self.setup_settings_tab()

    def create_toolbar(self):
        """Create the main toolbar with actions."""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)

        # New Post
        new_post_action = QAction(QIcon("resources/icons/new.png"), "New Post", self)
        new_post_action.triggered.connect(self.start_generation)
        toolbar.addAction(new_post_action)

        toolbar.addSeparator()

        # Preview
        preview_action = QAction(QIcon("resources/icons/preview.png"), "Preview", self)
        preview_action.triggered.connect(self.preview_blog_post)
        toolbar.addAction(preview_action)

        # Publish
        publish_action = QAction(QIcon("resources/icons/publish.png"), "Publish", self)
        publish_action.triggered.connect(self.post_to_blog)
        toolbar.addAction(publish_action)

        toolbar.addSeparator()

        # Settings
        settings_action = QAction(
            QIcon("resources/icons/settings.png"), "Settings", self
        )
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

    def setup_dashboard_tab(self):
        """Setup the dashboard tab with overview and quick actions."""
        dashboard = QWidget()
        layout = QVBoxLayout(dashboard)

        # Initialize analytics service
        self.analytics = AnalyticsService()

        # Quick Stats
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel)
        stats_layout = QHBoxLayout(stats_frame)

        # Posts Stats
        self.posts_stats = QLabel("Posts: 0")
        stats_layout.addWidget(self.posts_stats)

        # Views Stats
        self.views_stats = QLabel("Views: 0")
        stats_layout.addWidget(self.views_stats)

        # Engagement Stats
        self.engagement_stats = QLabel("Engagement: 0%")
        stats_layout.addWidget(self.engagement_stats)

        layout.addWidget(stats_frame)

        # Content Calendar
        calendar_frame = QFrame()
        calendar_frame.setFrameStyle(QFrame.StyledPanel)
        calendar_layout = QVBoxLayout(calendar_frame)

        calendar_label = QLabel("Content Calendar")
        calendar_label.setFont(QFont("Arial", 12, QFont.Bold))
        calendar_layout.addWidget(calendar_label)

        calendar = QCalendarWidget()
        calendar_layout.addWidget(calendar)

        layout.addWidget(calendar_frame)

        # Recent Posts
        recent_frame = QFrame()
        recent_frame.setFrameStyle(QFrame.StyledPanel)
        recent_layout = QVBoxLayout(recent_frame)

        recent_label = QLabel("Recent Posts")
        recent_label.setFont(QFont("Arial", 12, QFont.Bold))
        recent_layout.addWidget(recent_label)

        self.recent_list = QTextEdit()
        self.recent_list.setReadOnly(True)
        recent_layout.addWidget(self.recent_list)

        layout.addWidget(recent_frame)

        # Initialize charts
        charts_frame = QFrame()
        charts_layout = QVBoxLayout(charts_frame)

        # Add title labels and charts
        trends_label = QLabel("Content Trends")
        trends_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        charts_layout.addWidget(trends_label)
        self.trends_chart = AnalyticsChart()
        charts_layout.addWidget(self.trends_chart)

        dist_label = QLabel("Content Distribution")
        dist_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        charts_layout.addWidget(dist_label)
        self.dist_chart = DistributionChart()
        charts_layout.addWidget(self.dist_chart)

        engagement_label = QLabel("Engagement Analysis")
        engagement_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        charts_layout.addWidget(engagement_label)
        self.engagement_chart = EngagementPieChart()
        charts_layout.addWidget(self.engagement_chart)

        # Add charts to main layout
        layout.addWidget(charts_frame)

        # Update dashboard data
        self.update_dashboard()

        self.tab_widget.addTab(dashboard, "Dashboard")

    def update_dashboard(self):
        """Update dashboard with current analytics data."""
        try:
            # Get current statistics
            stats = self.analytics.get_current_stats()

            # Update quick stats
            self.posts_stats.setText(f"Total Posts: {stats['total_posts']}")
            self.views_stats.setText(f"Total Views: {stats['total_views']:,}")
            self.engagement_stats.setText(
                f"Engagement Rate: {stats['engagement_rate']:.1f}%"
            )

            # Update recent posts list
            self.recent_list.clear()
            for post in stats["recent_posts"]:
                self.recent_list.addItem(
                    f"{post['title']} ({post['date']}) - "
                    f"Views: {post['views']:,}, "
                    f"Likes: {post['likes']:,}, "
                    f"Comments: {post['comments']:,}"
                )

            # Update charts
            self.trends_chart.update_data(stats["trends"])
            self.dist_chart.update_data(stats["distribution"])
            self.engagement_chart.update_data(stats["distribution"])

        except Exception as e:
            print(f"Error updating dashboard: {e}")

    def setup_devlog_tab(self):
        """Setup the DevLog Generator tab for content generation and scheduling."""
        devlog = QWidget()
        layout = QVBoxLayout(devlog)
        layout.setSpacing(20)  # Add more space between sections

        # Content Generation Section
        gen_frame = QFrame()
        gen_frame.setFrameStyle(QFrame.StyledPanel)
        gen_frame.setStyleSheet(
            """
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            QLabel {
                color: #2c3e50;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QLineEdit, QComboBox, QSpinBox {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 2px solid #3498db;
            }
        """
        )
        gen_layout = QVBoxLayout(gen_frame)
        gen_layout.setSpacing(15)

        # Title with icon
        title_layout = QHBoxLayout()
        gen_title = QLabel("DevLog Content Generator")
        gen_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_layout.addWidget(gen_title)
        title_layout.addStretch()
        gen_layout.addLayout(title_layout)

        # Topic Input with improved styling
        topic_frame = QFrame()
        topic_frame.setStyleSheet(
            "background-color: #f8f9fa; border-radius: 8px; padding: 10px;"
        )
        topic_layout = QVBoxLayout(topic_frame)
        topic_label = QLabel("Topic/Keywords")
        topic_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText(
            "Enter topic or keywords for content generation"
        )
        self.topic_input.setMinimumHeight(40)
        topic_layout.addWidget(topic_label)
        topic_layout.addWidget(self.topic_input)
        gen_layout.addWidget(topic_frame)

        # Generation Controls in a styled frame
        controls_frame = QFrame()
        controls_frame.setStyleSheet(
            "background-color: #f8f9fa; border-radius: 8px; padding: 10px;"
        )
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setSpacing(20)

        # Style Selection with improved layout
        style_layout = QVBoxLayout()
        style_label = QLabel("Content Style")
        style_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.style_combo = QComboBox()
        self.style_combo.addItems(
            ["Technical", "Tutorial", "Update", "Review", "Discussion"]
        )
        self.style_combo.setMinimumHeight(35)
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        controls_layout.addLayout(style_layout)

        # Length Control with improved layout
        length_layout = QVBoxLayout()
        length_label = QLabel("Content Length")
        length_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.length_spin = QSpinBox()
        self.length_spin.setRange(500, 5000)
        self.length_spin.setValue(1500)
        self.length_spin.setSingleStep(100)
        self.length_spin.setMinimumHeight(35)
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_spin)
        controls_layout.addLayout(length_layout)

        # Generate Button with improved styling
        self.generate_btn = QPushButton("Generate Content")
        self.generate_btn.setMinimumHeight(45)
        self.generate_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.generate_btn.clicked.connect(self.start_generation)
        controls_layout.addWidget(self.generate_btn)

        gen_layout.addWidget(controls_frame)

        # Progress Bar with improved styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 5px;
            }
        """
        )
        gen_layout.addWidget(self.progress_bar)

        # Generation Log with improved styling
        log_frame = QFrame()
        log_frame.setStyleSheet(
            "background-color: #f8f9fa; border-radius: 8px; padding: 10px;"
        )
        log_layout = QVBoxLayout(log_frame)
        log_label = QLabel("Generation Log")
        log_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(
            """
            QTextEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
            }
        """
        )
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_output)
        gen_layout.addWidget(log_frame)

        layout.addWidget(gen_frame)

        # Content Preview and Scheduling Section
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.StyledPanel)
        preview_frame.setStyleSheet(
            """
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            QCalendarWidget {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
            }
            QCalendarWidget QToolButton {
                color: #2c3e50;
                background-color: transparent;
                border: none;
                padding: 5px;
            }
            QCalendarWidget QMenu {
                background-color: white;
                border: 1px solid #bdc3c7;
            }
            QCalendarWidget QSpinBox {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                padding: 3px;
            }
        """
        )
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setSpacing(15)

        # Preview Title with icon
        preview_title = QLabel("Content Preview & Schedule")
        preview_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        preview_layout.addWidget(preview_title)

        # Preview Area with improved styling
        preview_area = QFrame()
        preview_area.setStyleSheet(
            "background-color: #f8f9fa; border-radius: 8px; padding: 10px;"
        )
        preview_area_layout = QVBoxLayout(preview_area)
        self.preview_web = QWebEngineView()
        self.preview_web.setMinimumHeight(300)
        preview_area_layout.addWidget(self.preview_web)
        preview_layout.addWidget(preview_area)

        # Scheduling Controls with improved layout
        schedule_frame = QFrame()
        schedule_frame.setStyleSheet(
            "background-color: #f8f9fa; border-radius: 8px; padding: 10px;"
        )
        schedule_layout = QHBoxLayout(schedule_frame)
        schedule_layout.setSpacing(20)

        # Calendar with improved layout
        calendar_layout = QVBoxLayout()
        date_label = QLabel("Select Publish Date")
        date_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.publish_calendar = QCalendarWidget()
        self.publish_calendar.setMinimumDate(datetime.now())
        self.publish_calendar.clicked.connect(self.on_date_selected)
        calendar_layout.addWidget(date_label)
        calendar_layout.addWidget(self.publish_calendar)
        schedule_layout.addLayout(calendar_layout)

        # Action buttons with improved styling
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)

        self.schedule_btn = QPushButton("Schedule Post")
        self.schedule_btn.setMinimumHeight(45)
        self.schedule_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.schedule_btn.clicked.connect(self.schedule_post)
        self.schedule_btn.setEnabled(False)
        buttons_layout.addWidget(self.schedule_btn)

        self.publish_btn = QPushButton("Publish Now")
        self.publish_btn.setMinimumHeight(45)
        self.publish_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.publish_btn.clicked.connect(self.post_to_blog)
        self.publish_btn.setEnabled(False)
        buttons_layout.addWidget(self.publish_btn)

        schedule_layout.addLayout(buttons_layout)
        preview_layout.addWidget(schedule_frame)

        layout.addWidget(preview_frame)

        # Add the tab
        self.tab_widget.addTab(devlog, "DevLog Generator")

    def on_date_selected(self, date):
        """Handle date selection in the calendar."""
        if not hasattr(self, "latest_output_path") or not self.latest_output_path:
            QMessageBox.warning(self, "Warning", "Please generate content first.")
            self.publish_calendar.setSelectedDate(datetime.now())
            return

        # Enable scheduling button when a future date is selected
        self.schedule_btn.setEnabled(date > datetime.now())

    def schedule_post(self):
        """Schedule the generated content for publishing."""
        if not hasattr(self, "latest_output_path") or not self.latest_output_path:
            QMessageBox.warning(self, "Warning", "No content has been generated yet.")
            return

        selected_date = self.publish_calendar.selectedDate().toPyDate()

        if selected_date <= datetime.now().date():
            QMessageBox.warning(
                self, "Warning", "Please select a future date for scheduling."
            )
            return

        try:
            # Create scheduled_posts directory if it doesn't exist
            scheduled_dir = Path("scheduled_posts")
            scheduled_dir.mkdir(exist_ok=True)

            # Create a metadata file for the scheduled post
            post_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            metadata = {
                "post_id": post_id,
                "scheduled_date": selected_date.isoformat(),
                "content_path": str(self.latest_output_path),
                "topic": self.topic_input.text(),
                "style": self.style_combo.currentText(),
                "length": self.length_spin.value(),
            }

            # Save metadata
            metadata_path = scheduled_dir / f"{post_id}_metadata.json"
            import json

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            QMessageBox.information(
                self,
                "Success",
                f"Post scheduled for {selected_date.strftime('%Y-%m-%d')}",
            )

            # Update dashboard to show scheduled post
            self.update_dashboard()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to schedule post: {str(e)}")

    def setup_editor_tab(self):
        """Setup the blog post editor tab."""
        editor = QWidget()
        layout = QVBoxLayout(editor)

        # Editor Controls
        controls_layout = QHBoxLayout()

        # Model Selection
        model_label = QLabel("AI Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["GPT-4", "Mistral", "Custom"])
        controls_layout.addWidget(model_label)
        controls_layout.addWidget(self.model_combo)

        # Style Selection
        style_label = QLabel("Style:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Professional", "Casual", "Technical", "Creative"])
        controls_layout.addWidget(style_label)
        controls_layout.addWidget(self.style_combo)

        # Length Control
        length_label = QLabel("Length:")
        self.length_spin = QSpinBox()
        self.length_spin.setRange(500, 5000)
        self.length_spin.setSingleStep(100)
        self.length_spin.setValue(1000)
        controls_layout.addWidget(length_label)
        controls_layout.addWidget(self.length_spin)

        layout.addLayout(controls_layout)

        # Editor Area
        editor_splitter = QSplitter(Qt.Vertical)

        # Input Area
        input_frame = QFrame()
        input_layout = QVBoxLayout(input_frame)

        input_label = QLabel("Topic/Prompt")
        input_label.setFont(QFont("Arial", 10, QFont.Bold))
        input_layout.addWidget(input_label)

        self.input_text = QTextEdit()
        input_layout.addWidget(self.input_text)

        editor_splitter.addWidget(input_frame)

        # Output Area
        output_frame = QFrame()
        output_layout = QVBoxLayout(output_frame)

        output_label = QLabel("Generated Content")
        output_label.setFont(QFont("Arial", 10, QFont.Bold))
        output_layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)

        editor_splitter.addWidget(output_frame)

        layout.addWidget(editor_splitter)

        # Action Buttons
        button_layout = QHBoxLayout()

        generate_button = QPushButton("Generate")
        generate_button.clicked.connect(self.start_generation)
        button_layout.addWidget(generate_button)

        preview_button = QPushButton("Preview")
        preview_button.clicked.connect(self.preview_blog_post)
        button_layout.addWidget(preview_button)

        publish_button = QPushButton("Publish")
        publish_button.clicked.connect(self.post_to_blog)
        button_layout.addWidget(publish_button)

        layout.addLayout(button_layout)

        self.tab_widget.addTab(editor, "Editor")

    def setup_analytics_tab(self):
        """Setup the analytics tab with interactive charts."""
        analytics_tab = QWidget()
        layout = QVBoxLayout(analytics_tab)

        # Create splitter for flexible layout
        splitter = QSplitter(Qt.Vertical)

        # Top section: Trends chart
        trends_frame = QFrame()
        trends_frame.setFrameStyle(QFrame.StyledPanel)
        trends_layout = QVBoxLayout(trends_frame)
        trends_layout.addWidget(QLabel("Content Trends"))
        self.trends_chart = AnalyticsChart()
        trends_layout.addWidget(self.trends_chart)
        splitter.addWidget(trends_frame)

        # Middle section: Distribution charts
        dist_frame = QFrame()
        dist_frame.setFrameStyle(QFrame.StyledPanel)
        dist_layout = QVBoxLayout(dist_frame)
        dist_layout.addWidget(QLabel("Content Distribution"))
        self.dist_chart = DistributionChart()
        dist_layout.addWidget(self.dist_chart)
        splitter.addWidget(dist_frame)

        # Bottom section: Engagement breakdown
        engagement_frame = QFrame()
        engagement_frame.setFrameStyle(QFrame.StyledPanel)
        engagement_layout = QVBoxLayout(engagement_frame)
        engagement_layout.addWidget(QLabel("Engagement Breakdown"))
        self.engagement_chart = EngagementPieChart()
        engagement_layout.addWidget(self.engagement_chart)
        splitter.addWidget(engagement_frame)

        # Set initial splitter sizes
        splitter.setSizes([400, 300, 300])

        layout.addWidget(splitter)
        self.tab_widget.addTab(analytics_tab, "Analytics")

    def setup_settings_tab(self):
        """Setup the settings tab with configuration options."""
        settings = QWidget()
        layout = QVBoxLayout(settings)

        # WordPress Settings
        wp_frame = QFrame()
        wp_frame.setFrameStyle(QFrame.StyledPanel)
        wp_layout = QVBoxLayout(wp_frame)

        wp_label = QLabel("WordPress Settings")
        wp_label.setFont(QFont("Arial", 12, QFont.Bold))
        wp_layout.addWidget(wp_label)

        # Add WordPress configuration controls
        wp_controls = QWidget()
        wp_controls_layout = QVBoxLayout(wp_controls)

        # URL
        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        self.url_input = QLineEdit()
        self.url_input.setText(self.config.get("wordpress", "url", fallback=""))
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        wp_controls_layout.addLayout(url_layout)

        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.username_input.setText(
            self.config.get("wordpress", "username", fallback="")
        )
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        wp_controls_layout.addLayout(username_layout)

        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText(
            self.config.get("wordpress", "password", fallback="")
        )
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        wp_controls_layout.addLayout(password_layout)

        wp_layout.addWidget(wp_controls)
        layout.addWidget(wp_frame)

        # Save Button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.tab_widget.addTab(settings, "Settings")

    def save_settings(self):
        """Save the current settings."""
        try:
            self.config["wordpress"]["url"] = self.url_input.text()
            self.config["wordpress"]["username"] = self.username_input.text()
            self.config["wordpress"]["password"] = self.password_input.text()

            with open(
                Path(__file__).resolve().parent.parent / "config" / "config.ini", "w"
            ) as f:
                self.config.write(f)

            self.wordpress_client = WordPressClient(self.config)
            self.statusBar.showMessage("Settings saved successfully", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")

    def start_generation(self):
        """Start the content generation process."""
        # Get parameters from UI
        topic = self.topic_input.text().strip()
        style = self.style_combo.currentText()
        length = self.length_spin.value()

        if not topic:
            QMessageBox.warning(self, "Input Error", "Please enter a topic.")
            return

        # Show progress UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()
        self.toggle_buttons(False)

        # Create worker thread
        self.worker = WorkerThread()
        self.worker.finished.connect(self.generation_finished)
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.update_log)

        # Set parameters for devlog generation
        context = {
            "topic": topic,
            "style": style,
            "length": length,
            "keywords": topic,  # Using topic as keywords for now
        }

        # Start generation
        self.worker.set_params(context)
        self.worker.start()

    def generation_finished(self, result):
        """Handle completion of content generation."""
        self.progress_bar.setValue(100)
        self.toggle_buttons(True)

        if result:
            # Update preview with the generated devlog
            self.preview_web.setHtml(result)

            # Enable scheduling/publishing
            self.schedule_btn.setEnabled(True)
            self.publish_btn.setEnabled(True)

            # Save the devlog
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"output/devlog_{timestamp}.html"
            self.devlog_service.save_devlog(result, output_path)

            QMessageBox.information(
                self,
                "Success",
                f"Devlog generated successfully!\nSaved to: {output_path}",
            )
        else:
            QMessageBox.warning(self, "Error", "Failed to generate devlog.")

    def update_log(self, message):
        """Update the log output with a message."""
        self.log_output.append(message)

    def update_progress(self, value):
        """Update the progress bar."""
        self.progress_bar.setValue(value)

    def toggle_buttons(self, enabled):
        """Enable/disable UI buttons."""
        self.generate_btn.setEnabled(enabled)
        self.schedule_btn.setEnabled(enabled)
        self.publish_btn.setEnabled(enabled)

    def preview_blog_post(self):
        """Preview the latest generated blog post."""
        if not self.latest_output_path:
            QMessageBox.warning(
                self, "No Output", "No blog post has been generated yet."
            )
            return

        if not Path(self.latest_output_path).exists():
            QMessageBox.warning(
                self, "File Not Found", "The latest blog post file does not exist."
            )
            return

        self.web_view = QWebEngineView()
        self.web_view.setUrl(
            QUrl.fromLocalFile(str(Path(self.latest_output_path).resolve()))
        )
        self.web_view.show()

    def post_to_blog(self):
        """Post the latest generated blog to WordPress."""
        if not self.latest_output_path:
            QMessageBox.warning(
                self, "No Blog Post", "No blog post available to upload."
            )
            return

        try:
            with open(self.latest_output_path, "r", encoding="utf-8") as f:
                content_html = f.read()

            blog_post = self.vector_db.extract_blog_post(content_html)
            response = self.wordpress_client.post_to_wordpress(
                title=blog_post.title,
                content=content_html,
                excerpt=blog_post.excerpt,
                categories=self.vector_db.get_categories(),
                tags=self.vector_db.get_tags(),
            )

            if response:
                self.statusBar.showMessage(f"Blog posted: {response['link']}", 3000)
                QMessageBox.information(
                    self, "Success", f"Blog posted: {response['link']}"
                )
            else:
                self.statusBar.showMessage("Failed to post blog", 3000)
                QMessageBox.warning(
                    self, "Error", "Failed to post blog. Check logs for details."
                )
        except Exception as e:
            self.statusBar.showMessage(f"Error: {e}", 3000)
            QMessageBox.warning(self, "Error", f"Failed to post blog: {e}")

    def open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            self.wordpress_client.update_settings(settings)
            self.statusBar.showMessage("Settings saved", 3000)
            QMessageBox.information(
                self, "Settings Saved", "Your settings have been saved."
            )
            self.vector_db.reload_vector_db()

    def launch_setup_wizard(self, config_path: Path):
        """
        Launches the setup wizard to create config.ini.
        """
        wizard = SetupWizardDialog(self)
        if wizard.exec_() == QDialog.Accepted:
            # After successful setup, initialize services and UI
            self.config.read(str(config_path))
            self.vector_db = VectorDB()
            self.wordpress_client = WordPressClient(self.config)
            self.init_ui()
            self.latest_output_path = ""
        else:
            # If the user cancels the setup, exit the application
            QMessageBox.critical(
                self,
                "Setup Incomplete",
                "Configuration is required to run the application. Exiting.",
            )
            sys.exit(1)

    def generate_post(self):
        """Generate a blog post using the modular pipeline."""
        try:
            # Get input values
            topic = self.topic_input.text().strip()
            style = self.style_combo.currentText().lower()
            length = self.length_spin.value()

            if not topic:
                QMessageBox.warning(self, "Input Error", "Please enter a topic.")
                return

            # Update UI state
            self.generate_button.setEnabled(False)
            self.status_label.setText("Generating post...")
            QApplication.processEvents()

            # Initialize services
            services = self.setup_services()
            generator = BlogGenerator(
                mistral_client=services["client"], vector_db=services["vector_db"]
            )

            # Generate post
            polished = generator.generate_post(
                prompt=topic, style=style, target_length=length
            )

            # Get devlog entry
            devlog_entry = generator.devlog_service.get_entry_by_post_id(
                polished.metadata.get("post_id", "")
            )

            # Update editor with polished content
            self.editor.setPlainText(polished.content)

            # Update devlog display
            if devlog_entry:
                self.devlog_output.setPlainText(devlog_entry.ai_summary)

                # Add to devlog list
                self.devlog_list.addItem(
                    f"{devlog_entry.timestamp.strftime('%Y-%m-%d %H:%M')} - {topic}"
                )

            # Update status
            self.status_label.setText("Done ✅")

            # Show success message
            QMessageBox.information(
                self,
                "Success",
                f"Blog post generated successfully!\n\n"
                f"Topic: {topic}\n"
                f"Style: {style}\n"
                f"Length: {length} words",
            )

        except Exception as e:
            logger.error(f"Error generating post: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to generate blog post:\n{str(e)}"
            )
            self.status_label.setText("Error ❌")

        finally:
            self.generate_button.setEnabled(True)

    def setup_services(self) -> Dict:
        """Initialize and return required services."""
        # Get API key
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found in environment variables")

        # Initialize Mistral client
        client = MistralClient(api_key=api_key)

        # Initialize VectorDB
        vector_db = VectorDB()

        return {"client": client, "vector_db": vector_db}

    def _connect_signals(self):
        """Connect UI signals to slots."""
        # Find DevlogHistoryPanel
        history_panel = self.tab_widget.widget(2)  # Index 2 is Devlog History tab
        if isinstance(history_panel, DevlogHistoryPanel):
            history_panel.devlog_selected.connect(self._on_devlog_selected)
            history_panel.devlog_published.connect(self._on_devlog_published)

    def _on_devlog_selected(self, entry: DevlogEntry):
        """Handle devlog selection."""
        # Update preview panel if we're on the devlog tab
        if self.tab_widget.currentIndex() == 1:  # Devlog Generator tab
            self.preview_web.setHtml(entry.content)
            self.schedule_btn.setEnabled(True)
            self.publish_btn.setEnabled(True)

    def _on_devlog_published(self, entry: DevlogEntry, platforms: List[str]):
        """Handle devlog publishing."""
        try:
            # Mark as published in harvester
            self.harvester.mark_as_published(entry, platforms)

            # Show success message
            QMessageBox.information(
                self, "Success", f"Devlog published to: {', '.join(platforms)}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to publish devlog: {str(e)}")
