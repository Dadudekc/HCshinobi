#!/usr/bin/env python3

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dreamos_boot.log')
    ]
)

class DreamOSBoot:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.monitoring_dir = self.root_dir / "tools" / "monitoring"
        self.monitoring_process: Optional[subprocess.Popen] = None
        self.services_healthy = False

    def start_monitoring(self) -> bool:
        """Start the monitoring stack and wait for health checks."""
        try:
            script_path = self.monitoring_dir / "start_monitoring.sh"
            logging.info("Starting monitoring stack...")
            
            # Ensure script is executable
            script_path.chmod(0o755)
            
            self.monitoring_process = subprocess.Popen(
                ["bash", str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait for services to be healthy
            max_attempts = 30
            attempt = 0
            while attempt < max_attempts:
                if self._check_monitoring_health():
                    logging.info("✅ Monitoring stack is healthy")
                    return True
                time.sleep(2)
                attempt += 1
            
            logging.error("❌ Monitoring stack failed to become healthy")
            return False
            
        except Exception as e:
            logging.error(f"Failed to start monitoring stack: {e}")
            return False

    def _check_monitoring_health(self) -> bool:
        """Check if Prometheus and Grafana are responding."""
        import requests
        try:
            # Check Prometheus
            prom_response = requests.get("http://localhost:9090/-/ready")
            if prom_response.status_code != 200:
                return False
            
            # Check Grafana
            grafana_response = requests.get("http://localhost:3000/api/health")
            if grafana_response.status_code != 200:
                return False
                
            return True
        except requests.exceptions.RequestException:
            return False

    def start_core_services(self) -> bool:
        """Start Dream.OS core services."""
        try:
            # Start CursorResultListener
            logging.info("Starting CursorResultListener...")
            subprocess.Popen(
                [sys.executable, "-m", "tools.cursor_result_listener"],
                env=dict(os.environ, METRICS_PORT="8000")
            )
            
            # Start WorkflowAgent
            logging.info("Starting WorkflowAgent...")
            subprocess.Popen(
                [sys.executable, "-m", "agents.workflow_agent"],
                env=dict(os.environ, METRICS_PORT="8001")
            )
            
            # Start FeedbackConsumer
            logging.info("Starting FeedbackConsumer...")
            subprocess.Popen(
                [sys.executable, "-m", "services.feedback_consumer"],
                env=dict(os.environ, METRICS_PORT="8002")
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to start core services: {e}")
            return False

    def shutdown(self):
        """Graceful shutdown of Dream.OS services."""
        if self.monitoring_process:
            logging.info("Shutting down monitoring stack...")
            subprocess.run(
                ["docker-compose", "down"],
                cwd=str(self.monitoring_dir)
            )

def main():
    boot = DreamOSBoot()
    
    try:
        # Start monitoring first
        if not boot.start_monitoring():
            logging.error("Failed to start monitoring. Aborting boot.")
            sys.exit(1)
        
        # Start core services
        if not boot.start_core_services():
            logging.error("Failed to start core services. Aborting boot.")
            boot.shutdown()
            sys.exit(1)
        
        logging.info("🚀 Dream.OS boot sequence completed successfully")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("Received shutdown signal")
        boot.shutdown()
    except Exception as e:
        logging.error(f"Unexpected error during boot: {e}")
        boot.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    main() 