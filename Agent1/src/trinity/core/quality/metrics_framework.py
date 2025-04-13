"""
Quality Metrics Framework
Defines and tracks quality metrics across the system.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import re
import ast
from collections import defaultdict

@dataclass
class QualityMetric:
    name: str
    category: str
    value: float
    timestamp: float
    threshold: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

class QualityMetricsFramework:
    def __init__(self, metrics_dir: str = "metrics/quality"):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.logger = self._setup_logging()
        self.metrics: List[QualityMetric] = []
        
        # Register default metric collectors
        self.metric_collectors: Dict[str, Callable] = {
            "code_coverage": self._collect_coverage_metrics,
            "code_complexity": self._collect_complexity_metrics,
            "test_success_rate": self._collect_test_metrics,
            "documentation_coverage": self._collect_documentation_metrics,
            "type_hint_coverage": self._collect_type_hint_metrics
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Configure logging for quality metrics."""
        logger = logging.getLogger("quality_metrics")
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler = logging.FileHandler(
            self.metrics_dir / "quality.log"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
        
    def register_metric_collector(self, name: str, collector: Callable):
        """Register a new metric collector."""
        self.metric_collectors[name] = collector
        self.logger.info(f"Registered metric collector: {name}")
        
    def collect_all_metrics(self):
        """Collect all registered metrics."""
        for name, collector in self.metric_collectors.items():
            try:
                collector()
            except Exception as e:
                self.logger.error(f"Error collecting {name} metrics", exc_info=True)
                
    def _collect_coverage_metrics(self):
        """Collect code coverage metrics."""
        try:
            import coverage
            cov = coverage.Coverage()
            cov.load()
            
            total = cov.report(show_missing=False)
            missing_lines = cov.get_missing()
            
            self._record_metric(
                "code_coverage",
                "testing",
                total,
                threshold=80.0,
                details={"missing_lines": missing_lines}
            )
        except ImportError:
            self.logger.warning("coverage package not installed")
            
    def _collect_complexity_metrics(self):
        """Collect code complexity metrics."""
        try:
            import radon.complexity as cc
            
            total_complexity = 0
            file_complexities = {}
            
            for py_file in Path("src").rglob("*.py"):
                with open(py_file) as f:
                    code = f.read()
                    
                try:
                    complexity = cc.cc_visit(code)
                    avg_complexity = sum(c.complexity for c in complexity) / len(complexity) if complexity else 0
                    file_complexities[str(py_file)] = avg_complexity
                    total_complexity += avg_complexity
                except:
                    continue
                    
            avg_complexity = total_complexity / len(file_complexities) if file_complexities else 0
            
            self._record_metric(
                "code_complexity",
                "code_quality",
                avg_complexity,
                threshold=10.0,
                details={"file_complexities": file_complexities}
            )
        except ImportError:
            self.logger.warning("radon package not installed")
            
    def _collect_test_metrics(self):
        """Collect test success metrics."""
        try:
            import pytest
            
            class TestResultCollector:
                def __init__(self):
                    self.total = 0
                    self.passed = 0
                    self.failed = 0
                    self.skipped = 0
                    
                def pytest_runtest_logreport(self, report):
                    if report.when == 'call':
                        self.total += 1
                        if report.passed:
                            self.passed += 1
                        elif report.failed:
                            self.failed += 1
                        elif report.skipped:
                            self.skipped += 1
                            
            collector = TestResultCollector()
            pytest.main(['tests'], plugins=[collector])
            
            success_rate = (collector.passed / collector.total * 100) if collector.total > 0 else 0
            
            self._record_metric(
                "test_success_rate",
                "testing",
                success_rate,
                threshold=95.0,
                details={
                    "total": collector.total,
                    "passed": collector.passed,
                    "failed": collector.failed,
                    "skipped": collector.skipped
                }
            )
        except ImportError:
            self.logger.warning("pytest package not installed")
            
    def _collect_documentation_metrics(self):
        """Collect documentation coverage metrics."""
        total_functions = 0
        documented_functions = 0
        file_coverage = {}
        
        for py_file in Path("src").rglob("*.py"):
            with open(py_file) as f:
                try:
                    tree = ast.parse(f.read())
                    file_functions = 0
                    file_documented = 0
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            file_functions += 1
                            if ast.get_docstring(node):
                                file_documented += 1
                                
                    if file_functions > 0:
                        coverage = (file_documented / file_functions * 100)
                        file_coverage[str(py_file)] = coverage
                        total_functions += file_functions
                        documented_functions += file_documented
                except:
                    continue
                    
        total_coverage = (documented_functions / total_functions * 100) if total_functions > 0 else 0
        
        self._record_metric(
            "documentation_coverage",
            "code_quality",
            total_coverage,
            threshold=90.0,
            details={"file_coverage": file_coverage}
        )
        
    def _collect_type_hint_metrics(self):
        """Collect type hint coverage metrics."""
        total_functions = 0
        typed_functions = 0
        file_coverage = {}
        
        for py_file in Path("src").rglob("*.py"):
            with open(py_file) as f:
                try:
                    tree = ast.parse(f.read())
                    file_functions = 0
                    file_typed = 0
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            file_functions += 1
                            has_return_type = node.returns is not None
                            has_arg_types = all(
                                arg.annotation is not None 
                                for arg in node.args.args
                            )
                            if has_return_type and has_arg_types:
                                file_typed += 1
                                
                    if file_functions > 0:
                        coverage = (file_typed / file_functions * 100)
                        file_coverage[str(py_file)] = coverage
                        total_functions += file_functions
                        typed_functions += file_typed
                except:
                    continue
                    
        total_coverage = (typed_functions / total_functions * 100) if total_functions > 0 else 0
        
        self._record_metric(
            "type_hint_coverage",
            "code_quality",
            total_coverage,
            threshold=85.0,
            details={"file_coverage": file_coverage}
        )
        
    def _record_metric(self, name: str, category: str, value: float, 
                      threshold: Optional[float] = None,
                      details: Optional[Dict[str, Any]] = None):
        """Record a quality metric."""
        metric = QualityMetric(
            name=name,
            category=category,
            value=value,
            timestamp=datetime.now().timestamp(),
            threshold=threshold,
            details=details
        )
        
        self.metrics.append(metric)
        
        if threshold is not None and value < threshold:
            self.logger.warning(
                f"Quality metric {name} below threshold: {value:.2f} < {threshold}"
            )
            
    def get_latest_metrics(self) -> Dict[str, QualityMetric]:
        """Get the latest value for each metric."""
        latest_metrics = {}
        
        for metric in reversed(self.metrics):
            if metric.name not in latest_metrics:
                latest_metrics[metric.name] = metric
                
        return latest_metrics
        
    def get_metrics_by_category(self, category: str) -> List[QualityMetric]:
        """Get all metrics for a specific category."""
        return [m for m in self.metrics if m.category == category]
        
    def export_metrics(self, output_file: Optional[str] = None):
        """Export metrics to JSON file."""
        if output_file is None:
            output_file = self.metrics_dir / f"quality_metrics_{datetime.now():%Y%m%d_%H%M%S}.json"
            
        metrics_data = [
            {
                "name": m.name,
                "category": m.category,
                "value": m.value,
                "timestamp": m.timestamp,
                "threshold": m.threshold,
                "details": m.details
            }
            for m in self.metrics
        ]
        
        with open(output_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
            
        self.logger.info(f"Exported metrics to {output_file}")
        
    def get_failing_metrics(self) -> List[QualityMetric]:
        """Get metrics that are below their thresholds."""
        return [
            m for m in self.metrics 
            if m.threshold is not None and m.value < m.threshold
        ]
        
    def get_metrics_trend(self, metric_name: str, 
                         start_time: Optional[float] = None,
                         end_time: Optional[float] = None) -> List[QualityMetric]:
        """Get historical trend for a specific metric."""
        metrics = [m for m in self.metrics if m.name == metric_name]
        
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
            
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
            
        return sorted(metrics, key=lambda m: m.timestamp) 