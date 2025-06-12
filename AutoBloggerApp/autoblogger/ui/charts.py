from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QMenu,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta
import csv
import os


class BaseChart(QWidget):
    """Base class for all chart widgets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Container widget for plot
        self.plot_container = QWidget()
        self.plot_layout = QVBoxLayout()
        self.plot_container.setLayout(self.plot_layout)

        # Add container to main layout
        self.layout.addWidget(self.plot_container)

        # Add export button
        self.export_btn = QPushButton("Export")
        self.export_btn.setFixedWidth(100)
        self.export_btn.clicked.connect(self.show_export_menu)
        self.layout.addWidget(self.export_btn)

    def show_export_menu(self):
        """Show export menu with options."""
        menu = QMenu(self)
        export_png = QAction("Export as PNG", self)
        export_png.triggered.connect(self.export_png)
        menu.addAction(export_png)
        menu.exec_(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))

    def export_png(self):
        """Export chart as PNG."""
        # TODO: Implement PNG export
        pass

    def export_chart(self, format_type):
        """Export chart data in specified format."""
        if not hasattr(self, "plot_widget"):
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chart_export_{timestamp}"

        if format_type == "png":
            # Export plot as PNG
            self.plot_widget.export(filename + ".png")
        elif format_type == "csv":
            # Export data as CSV
            if hasattr(self, "get_data_for_export"):
                data = self.get_data_for_export()
                with open(filename + ".csv", "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(data)


class AnalyticsChart(BaseChart):
    """Chart for displaying analytics data."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True)

        # Add plot widget to container
        self.plot_layout.addWidget(self.plot_widget)

        # Add controls
        self.setup_controls()

    def setup_controls(self):
        """Setup chart controls."""
        controls_layout = QHBoxLayout()

        # Time range selector
        self.time_range = QComboBox()
        self.time_range.addItems(["Last 7 days", "Last 30 days", "Last 90 days"])
        controls_layout.addWidget(QLabel("Time Range:"))
        controls_layout.addWidget(self.time_range)

        # Metric toggles
        self.metric_toggles = {}
        metrics = ["Posts", "Views", "Likes", "Comments", "Engagement Rate"]
        for metric in metrics:
            toggle = QPushButton(metric)
            toggle.setCheckable(True)
            toggle.setChecked(True)  # All metrics visible by default
            toggle.clicked.connect(self.update_chart)
            self.metric_toggles[metric] = toggle
            controls_layout.addWidget(toggle)

        # Add controls to main layout
        self.layout.addLayout(controls_layout)

        # Store plot items for each metric
        self.plot_items = {}

    def update_data(self, data):
        """Update chart with new data."""
        self.data = data
        self.update_chart()

    def update_chart(self):
        """Update chart based on selected filters."""
        if not hasattr(self, "data"):
            return

        # Clear existing plots
        self.plot_widget.clear()
        self.plot_items.clear()

        # Get time range
        time_range = self.time_range.currentText()
        days = {
            "Last 7 days": 7,
            "Last 30 days": 30,
            "Last 90 days": 90,
        }[time_range]

        # Filter data by time range
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_data = {
                date: metrics
                for date, metrics in self.data.items()
                if datetime.fromisoformat(date) >= cutoff_date
            }
        else:
            filtered_data = self.data

        # Prepare x-axis (dates)
        dates = list(filtered_data.keys())
        x = list(range(len(dates)))

        # Plot each selected metric
        colors = {
            "Posts": (0.2, 0.6, 0.8),  # Blue
            "Views": (0.8, 0.2, 0.2),  # Red
            "Likes": (0.2, 0.8, 0.2),  # Green
            "Comments": (0.8, 0.8, 0.2),  # Yellow
            "Engagement Rate": (0.8, 0.2, 0.8),  # Purple
        }

        for metric, toggle in self.metric_toggles.items():
            if toggle.isChecked():
                # Get y values for this metric
                y = [
                    filtered_data[date][metric.lower().replace(" ", "_")]
                    for date in dates
                ]

                # Create plot item
                pen = pg.mkPen(color=colors[metric], width=2)
                plot_item = self.plot_widget.plot(
                    x=x,
                    y=y,
                    name=metric,
                    pen=pen,
                    symbol="o",
                    symbolSize=8,
                    symbolBrush=colors[metric],
                )
                self.plot_items[metric] = plot_item

        # Set x-axis labels
        axis = self.plot_widget.getAxis("bottom")
        axis.setTicks([[(i, date) for i, date in enumerate(dates)]])

        # Add legend
        self.plot_widget.addLegend()

    def get_data_for_export(self):
        """Get data for CSV export."""
        if not hasattr(self, "data"):
            return []

        # Get time range
        time_range = self.time_range.currentText()
        days = {
            "Last 7 days": 7,
            "Last 30 days": 30,
            "Last 90 days": 90,
        }[time_range]

        # Filter data
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_data = {
                date: metrics
                for date, metrics in self.data.items()
                if datetime.fromisoformat(date) >= cutoff_date
            }
        else:
            filtered_data = self.data

        # Prepare CSV data
        headers = ["Date"] + [
            metric
            for metric, toggle in self.metric_toggles.items()
            if toggle.isChecked()
        ]
        data = [headers]

        for date, metrics in filtered_data.items():
            row = [date]
            for metric in headers[1:]:
                row.append(metrics[metric.lower().replace(" ", "_")])
            data.append(row)

        return data


class DistributionChart(BaseChart):
    """Chart for displaying content distribution."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True)

        # Add plot widget to container
        self.plot_layout.addWidget(self.plot_widget)

        # Add controls
        self.setup_controls()

    def setup_controls(self):
        """Setup chart controls."""
        controls_layout = QHBoxLayout()

        # Distribution type selector
        self.dist_type = QComboBox()
        self.dist_type.addItems(["By Style", "By Model", "By Topic"])
        controls_layout.addWidget(QLabel("Distribution:"))
        controls_layout.addWidget(self.dist_type)

        # Add controls to main layout
        self.layout.addLayout(controls_layout)

    def update_data(self, data):
        """Update chart with new data."""
        self.data = data
        self.update_chart()

    def update_chart(self):
        """Update chart based on selected distribution type."""
        if not hasattr(self, "data"):
            return

        # Clear previous plot
        self.plot_widget.clear()

        # Get selected distribution type
        dist_type = self.dist_type.currentText()
        data_key = "posts_by_style" if dist_type == "By Style" else "posts_by_model"

        # Prepare data
        labels = []
        values = []
        for key, stats in self.data[data_key].items():
            labels.append(key)
            values.append(stats["count"])

        # Create bar chart
        if values:
            x = list(range(len(labels)))
            y = values

            # Create bar chart
            bargraph = pg.BarGraphItem(x=x, height=y, width=0.6, brush=(0.2, 0.6, 0.8))
            self.plot_widget.addItem(bargraph)

            # Set x-axis labels
            axis = self.plot_widget.getAxis("bottom")
            axis.setTicks([[(i, label) for i, label in enumerate(labels)]])

    def get_data_for_export(self):
        """Get data for CSV export."""
        if not hasattr(self, "data"):
            return []

        dist_type = self.dist_type.currentText()
        data_key = "posts_by_style" if dist_type == "By Style" else "posts_by_model"

        data = [[dist_type, "Count"]]
        for key, stats in self.data[data_key].items():
            data.append([key, stats["count"]])

        return data


class EngagementPieChart(BaseChart):
    """Chart for displaying engagement distribution."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True)

        # Add plot widget to container
        self.plot_layout.addWidget(self.plot_widget)

        # Add controls
        self.setup_controls()

    def setup_controls(self):
        """Setup chart controls."""
        controls_layout = QHBoxLayout()

        # Engagement type selector
        self.engagement_type = QComboBox()
        self.engagement_type.addItems(["By Platform", "By Content Type"])
        controls_layout.addWidget(QLabel("View:"))
        controls_layout.addWidget(self.engagement_type)

        # Add controls to main layout
        self.layout.addLayout(controls_layout)

    def update_data(self, data):
        """Update pie chart with new data."""
        self.data = data
        self.update_chart()

    def update_chart(self):
        """Update pie chart based on selected metric."""
        if not hasattr(self, "data"):
            return

        # Clear previous pie chart
        if self.pie is not None:
            self.plot_widget.removeItem(self.pie)

        # Get selected metric
        metric = self.engagement_type.currentText().lower()

        # Prepare data for pie chart
        labels = []
        values = []
        total = 0

        # First pass: calculate total
        for style, stats in self.data["posts_by_style"].items():
            total += stats["engagement"][metric]

        # Second pass: calculate percentages and prepare data
        for style, stats in self.data["posts_by_style"].items():
            value = stats["engagement"][metric]
            percentage = (value / total * 100) if total > 0 else 0

            # Store percentage for tooltip
            stats["engagement"][f"{metric}_percentage"] = percentage

            labels.append(style)
            values.append(value)

        # Create pie chart
        if values:
            # Normalize values for pie chart
            values_normalized = [v / total for v in values]

            # Create pie chart with custom colors
            colors = [
                (0.2, 0.6, 0.8),  # Blue
                (0.8, 0.2, 0.2),  # Red
                (0.2, 0.8, 0.2),  # Green
                (0.8, 0.8, 0.2),  # Yellow
                (0.8, 0.2, 0.8),  # Purple
                (0.2, 0.8, 0.8),  # Cyan
            ]

            self.pie = pg.PieChartItem(
                values=values_normalized,
                labels=labels,
                pen=pg.mkPen(color=(255, 255, 255), width=2),
                brush=[pg.mkBrush(color) for color in colors[: len(values)]],
            )
            self.plot_widget.addItem(self.pie)

    def get_data_for_export(self):
        """Get data for CSV export."""
        if not hasattr(self, "data"):
            return []

        metric = self.engagement_type.currentText().lower()
        data = [["Style", metric.capitalize(), "Percentage"]]

        total = sum(
            stats["engagement"][metric]
            for stats in self.data["posts_by_style"].values()
        )

        for style, stats in self.data["posts_by_style"].items():
            value = stats["engagement"][metric]
            percentage = (value / total * 100) if total > 0 else 0
            data.append([style, value, f"{percentage:.1f}%"])

        return data
