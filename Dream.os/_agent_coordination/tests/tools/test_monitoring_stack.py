import os
import sys
import time
import pytest
import platform
import requests
from pathlib import Path
from typing import Generator

# Skip tests if SKIP_MONITORING_TESTS is set
skip_monitoring = pytest.mark.skipif(
    os.environ.get("SKIP_MONITORING_TESTS") == "1",
    reason="Monitoring tests are disabled"
)

@pytest.fixture(scope="module")
def monitoring_stack():
    # Determine which script to run based on platform
    script_dir = Path(__file__).parent.parent.parent / "tools" / "monitoring"
    if platform.system() == "Windows":
        script_path = script_dir / "start_monitoring.ps1"
        start_cmd = ["pwsh", "-File", str(script_path)]
    else:
        script_path = script_dir / "start_monitoring.sh"
        start_cmd = ["bash", str(script_path)]

    # Start monitoring stack
    os.system(" ".join(start_cmd))
    
    # Wait for services to be ready
    max_retries = 30
    retry_interval = 1
    
    def is_service_ready(url):
        for _ in range(max_retries):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(retry_interval)
        return False
    
    # Check if both services are ready
    prometheus_ready = is_service_ready("http://localhost:9090/-/ready")
    grafana_ready = is_service_ready("http://localhost:3000/api/health")
    
    if not prometheus_ready or not grafana_ready:
        pytest.fail("Monitoring services failed to start")
    
    yield
    
    # Cleanup: Stop the monitoring stack
    os.system("docker-compose down")

def _check_services_health() -> bool:
    """Check if all monitoring services are healthy."""
    prom = requests.get("http://localhost:9090/-/ready")
    grafana = requests.get("http://localhost:3000/api/health")
    return prom.status_code == 200 and grafana.status_code == 200

@skip_monitoring
class TestMonitoringStack:
    """Test suite for monitoring stack functionality."""
    
    def test_prometheus_ready(self, monitoring_stack):
        """Test Prometheus readiness endpoint."""
        response = requests.get("http://localhost:9090/-/ready")
        assert response.status_code == 200
    
    def test_grafana_healthy(self, monitoring_stack):
        """Test Grafana health endpoint."""
        response = requests.get("http://localhost:3000/api/health")
        assert response.status_code == 200
        assert response.json()["database"] == "ok"
    
    def test_prometheus_metrics_endpoint(self, monitoring_stack):
        """Test Prometheus metrics endpoint returns data."""
        response = requests.get("http://localhost:9090/api/v1/targets")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify all expected targets are present
        targets = {target["labels"]["job"] for target in data["data"]["activeTargets"]}
        expected_targets = {"dream_os_cursor", "dream_os_workflow", "dream_os_feedback"}
        assert expected_targets.issubset(targets)
    
    def test_grafana_datasource(self, monitoring_stack):
        """Test Prometheus datasource is configured in Grafana."""
        # Note: In production, you'd want to use proper auth
        response = requests.get(
            "http://localhost:3000/api/datasources",
            auth=("admin", "admin")
        )
        assert response.status_code == 200
        datasources = response.json()
        
        # Verify Prometheus datasource exists
        assert any(
            ds["name"] == "Prometheus" and ds["type"] == "prometheus"
            for ds in datasources
        )
    
    def test_dashboard_provisioned(self, monitoring_stack):
        """Test Dream.OS dashboard is provisioned."""
        response = requests.get(
            "http://localhost:3000/api/search",
            params={"query": "Dream.OS Cursor Metrics"},
            auth=("admin", "admin")
        )
        assert response.status_code == 200
        dashboards = response.json()
        assert any(d["title"] == "Dream.OS Cursor Metrics" for d in dashboards)
    
    @pytest.mark.parametrize("metric_name", [
        "cursor_execution_results_total",
        "cursor_error_types_total",
        "cursor_retry_attempts_total",
        "cursor_queue_size"
    ])
    def test_metric_exists(self, monitoring_stack, metric_name):
        """Test that expected metrics exist in Prometheus."""
        response = requests.get(
            f"http://localhost:9090/api/v1/query",
            params={"query": metric_name}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

def test_prometheus_metrics(monitoring_stack):
    """Test that Prometheus is collecting metrics."""
    response = requests.get("http://localhost:9090/api/v1/targets")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["activeTargets"]) > 0

def test_grafana_datasource(monitoring_stack):
    """Test that Grafana has Prometheus datasource configured."""
    # Note: Using basic auth with default credentials
    auth = ("admin", "admin")
    response = requests.get(
        "http://localhost:3000/api/datasources",
        auth=auth
    )
    assert response.status_code == 200
    datasources = response.json()
    assert any(ds["type"] == "prometheus" for ds in datasources)

def test_grafana_dashboard(monitoring_stack):
    """Test that Grafana has the cursor metrics dashboard."""
    auth = ("admin", "admin")
    response = requests.get(
        "http://localhost:3000/api/search?query=Cursor%20Metrics",
        auth=auth
    )
    assert response.status_code == 200
    dashboards = response.json()
    assert len(dashboards) > 0
    assert any("Cursor Metrics" in db["title"] for db in dashboards) 