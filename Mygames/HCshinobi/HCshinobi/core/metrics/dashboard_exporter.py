"""Dashboard exporter for time-series metrics."""
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

logger = logging.getLogger(__name__)

class DashboardExporter:
    """Exports time-series metrics to interactive dashboards."""
    
    def __init__(self, bot_root: str = "HCshinobi"):
        """Initialize the dashboard exporter."""
        self.bot_root = Path(bot_root)
        self.metrics_dir = self.bot_root / "data" / "metrics"
        self.dashboards_dir = self.bot_root / "data" / "dashboards"
        self.dashboards_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_metrics_history(self, days: int = 30) -> pd.DataFrame:
        """Load metrics history for the specified number of days."""
        metrics_files = sorted(self.metrics_dir.glob("command_metrics_*.json"))
        if not metrics_files:
            return pd.DataFrame()
            
        # Load last N days of metrics
        cutoff_date = datetime.now() - timedelta(days=days)
        metrics_data = []
        
        for file in metrics_files[-days:]:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    # Add timestamp from filename
                    timestamp = datetime.strptime(file.stem.split("_")[-1], "%Y%m%d")
                    if timestamp >= cutoff_date:
                        for cmd, metrics in data.items():
                            metrics["command"] = cmd
                            metrics["timestamp"] = timestamp
                            metrics_data.append(metrics)
            except Exception as e:
                logger.error(f"Failed to load metrics file {file}: {e}")
                
        return pd.DataFrame(metrics_data)
        
    def _create_coverage_dashboard(self, df: pd.DataFrame) -> go.Figure:
        """Create a test coverage dashboard."""
        if df.empty:
            return go.Figure()
            
        # Calculate coverage metrics
        coverage_data = df.groupby("timestamp").agg({
            "total_uses": "sum",
            "successful_uses": "sum",
            "error_count": "sum"
        }).reset_index()
        
        coverage_data["success_rate"] = coverage_data["successful_uses"] / coverage_data["total_uses"]
        coverage_data["error_rate"] = coverage_data["error_count"] / coverage_data["total_uses"]
        
        # Create figure
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Command Usage", "Success & Error Rates"),
            vertical_spacing=0.2
        )
        
        # Add usage traces
        fig.add_trace(
            go.Scatter(
                x=coverage_data["timestamp"],
                y=coverage_data["total_uses"],
                name="Total Uses",
                line=dict(color="blue")
            ),
            row=1, col=1
        )
        
        # Add rate traces
        fig.add_trace(
            go.Scatter(
                x=coverage_data["timestamp"],
                y=coverage_data["success_rate"],
                name="Success Rate",
                line=dict(color="green")
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=coverage_data["timestamp"],
                y=coverage_data["error_rate"],
                name="Error Rate",
                line=dict(color="red")
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title="Command Coverage Dashboard",
            height=800,
            showlegend=True
        )
        
        return fig
        
    def _create_complexity_dashboard(self, df: pd.DataFrame) -> go.Figure:
        """Create a complexity metrics dashboard."""
        if df.empty:
            return go.Figure()
            
        # Calculate complexity metrics
        complexity_data = df.groupby("command").agg({
            "cyclomatic_complexity": "mean",
            "max_nesting": "mean",
            "branch_count": "mean",
            "error_rate": "mean"
        }).reset_index()
        
        # Create figure
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Cyclomatic Complexity",
                "Max Nesting Level",
                "Branch Count",
                "Error Rate"
            )
        )
        
        # Add complexity traces
        fig.add_trace(
            go.Bar(
                x=complexity_data["command"],
                y=complexity_data["cyclomatic_complexity"],
                name="Cyclomatic Complexity"
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=complexity_data["command"],
                y=complexity_data["max_nesting"],
                name="Max Nesting"
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(
                x=complexity_data["command"],
                y=complexity_data["branch_count"],
                name="Branch Count"
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=complexity_data["command"],
                y=complexity_data["error_rate"],
                name="Error Rate"
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title="Command Complexity Dashboard",
            height=800,
            showlegend=False
        )
        
        return fig
        
    def _create_priority_dashboard(self, df: pd.DataFrame) -> go.Figure:
        """Create a priority metrics dashboard."""
        if df.empty:
            return go.Figure()
            
        # Calculate priority metrics
        priority_data = df.groupby("command").agg({
            "priority_score": "mean",
            "total_uses": "sum",
            "error_rate": "mean"
        }).reset_index()
        
        # Create scatter plot
        fig = px.scatter(
            priority_data,
            x="total_uses",
            y="error_rate",
            size="priority_score",
            color="priority_score",
            hover_name="command",
            title="Command Priority Dashboard",
            labels={
                "total_uses": "Total Uses",
                "error_rate": "Error Rate",
                "priority_score": "Priority Score"
            }
        )
        
        return fig
        
    def export_dashboards(self, days: int = 30):
        """Export all dashboards for the specified time period."""
        try:
            # Load metrics data
            df = self._load_metrics_history(days)
            if df.empty:
                logger.warning("No metrics data available for dashboard generation")
                return
                
            # Generate dashboards
            coverage_fig = self._create_coverage_dashboard(df)
            complexity_fig = self._create_complexity_dashboard(df)
            priority_fig = self._create_priority_dashboard(df)
            
            # Save dashboards
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            coverage_fig.write_html(
                self.dashboards_dir / f"coverage_dashboard_{timestamp}.html"
            )
            complexity_fig.write_html(
                self.dashboards_dir / f"complexity_dashboard_{timestamp}.html"
            )
            priority_fig.write_html(
                self.dashboards_dir / f"priority_dashboard_{timestamp}.html"
            )
            
            logger.info(f"Exported dashboards to {self.dashboards_dir}")
            
        except Exception as e:
            logger.error(f"Failed to export dashboards: {e}")
            
    def get_latest_dashboard_links(self) -> Dict[str, str]:
        """Get links to the latest dashboard files."""
        dashboards = {}
        
        for metric_type in ["coverage", "complexity", "priority"]:
            pattern = f"{metric_type}_dashboard_*.html"
            files = sorted(self.dashboards_dir.glob(pattern))
            if files:
                dashboards[metric_type] = str(files[-1].relative_to(self.bot_root))
                
        return dashboards 