"""Dream.OS Deployment Agent - Cursor Listener Deployment Orchestrator"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pytest
import yaml
from prometheus_client.parser import text_string_to_metric_families

from core.config import config_service
from core.feedback import log_event
from core.utils.command import CommandExecutor
from core.utils.file_manager import FileManager
from core.utils.system import SystemUtils

AGENT_ID = "DeploymentAgent"
CURSOR_METRICS = [
    "cursor_execution_results",
    "cursor_error_types",
    "cursor_retry_attempts",
    "cursor_processing_duration_seconds",
    "cursor_queue_size"
]

class DeploymentAgent:
    """Orchestrates the deployment of the Cursor Result Listener."""
    
    def __init__(self):
        self.cmd = CommandExecutor()
        self.file_mgr = FileManager()
        self.sys_utils = SystemUtils()
        self.config = self._load_config()
        self.feedback_dir = Path(self.config["cursor"]["feedback_dir"])
        
    def _load_config(self) -> Dict:
        """Load and validate deployment configuration."""
        config_path = Path("config/cursor.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        required_keys = [
            "poll_interval", "metrics_port", "pending_dir",
            "processing_dir", "archive_dir", "error_dir",
            "feedback_dir", "context_file", "log_file"
        ]
        
        for key in required_keys:
            if key not in config["cursor"]:
                raise KeyError(f"Missing required config key: cursor.{key}")
                
        return config

    async def run_tests(self) -> bool:
        """Execute test suite and verify coverage."""
        log_event("TESTS_STARTED", AGENT_ID, {"component": "cursor_listener"})
        
        # Run pytest with coverage
        result = await self.cmd.run_command(
            "pytest tests/tools/test_cursor_result_listener.py -v "
            "--cov=tools.cursor_result_listener --cov-report=html"
        )
        
        if "failed" in result.lower():
            log_event("TESTS_FAILED", AGENT_ID, {"output": result})
            return False
            
        # Verify coverage threshold
        cov_report = Path("htmlcov/index.html").read_text()
        if "90%" not in cov_report:
            log_event("COVERAGE_INSUFFICIENT", AGENT_ID, {"threshold": "90%"})
            return False
            
        log_event("TESTS_PASSED", AGENT_ID, {"coverage": "≥90%"})
        return True

    async def prepare_system(self) -> bool:
        """Prepare system directories and permissions."""
        try:
            # Create directory structure
            dirs = [
                self.config["cursor"][key] for key in 
                ["pending_dir", "processing_dir", "archive_dir", "error_dir", "feedback_dir"]
            ]
            
            for dir_path in dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                os.chmod(dir_path, 0o755)
                
            # Configure log rotation
            logrotate_config = f"""
            {self.config['cursor']['log_file']} {{
                daily
                rotate 14
                compress
                delaycompress
                notifempty
                create 0644 dream dream
            }}
            """
            Path("/etc/logrotate.d/cursor-listener").write_text(logrotate_config)
            
            log_event("SYSTEM_PREPARED", AGENT_ID, {"directories": dirs})
            return True
            
        except Exception as e:
            log_event("SYSTEM_PREP_FAILED", AGENT_ID, {"error": str(e)})
            return False

    async def backup_existing(self) -> bool:
        """Create backups of existing data."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Backup context file
            context_file = Path(self.config["cursor"]["context_file"])
            if context_file.exists():
                backup_path = context_file.parent / f"context_{timestamp}.json.bak"
                self.file_mgr.safe_copy(context_file, backup_path)
            
            # Archive logs
            log_file = Path(self.config["cursor"]["log_file"])
            if log_file.exists():
                backup_path = log_file.parent / f"cursor_{timestamp}.log.bak"
                self.file_mgr.safe_copy(log_file, backup_path)
            
            # Snapshot metrics
            metrics_response = await self.cmd.run_command(
                f"curl -s localhost:{self.config['cursor']['metrics_port']}/metrics"
            )
            metrics_path = Path("metrics") / f"cursor_metrics_{timestamp}.txt"
            metrics_path.write_text(metrics_response)
            
            log_event("BACKUP_CREATED", AGENT_ID, {"timestamp": timestamp})
            return True
            
        except Exception as e:
            log_event("BACKUP_FAILED", AGENT_ID, {"error": str(e)})
            return False

    async def deploy_service(self) -> bool:
        """Deploy and start the Cursor Listener service."""
        try:
            # Stop existing service
            await self.cmd.run_command("systemctl stop cursor-listener")
            
            # Update systemd service file
            service_config = f"""
            [Unit]
            Description=Dream OS Cursor Result Listener
            After=network.target

            [Service]
            Type=simple
            User=dream
            Group=dream
            WorkingDirectory=/opt/dream
            ExecStart=/usr/bin/python3 -m tools.cursor_result_listener
            Restart=always
            RestartSec=5

            [Install]
            WantedBy=multi-user.target
            """
            
            service_path = Path("/etc/systemd/system/cursor-listener.service")
            service_path.write_text(service_config)
            
            # Reload systemd and start service
            await self.cmd.run_command("systemctl daemon-reload")
            await self.cmd.run_command("systemctl start cursor-listener")
            
            # Verify service status
            status = await self.cmd.run_command("systemctl is-active cursor-listener")
            if "active" not in status.lower():
                raise RuntimeError("Service failed to start")
                
            log_event("SERVICE_DEPLOYED", AGENT_ID, {"status": "active"})
            return True
            
        except Exception as e:
            log_event("DEPLOYMENT_FAILED", AGENT_ID, {"error": str(e)})
            return False

    async def verify_deployment(self) -> bool:
        """Run post-deployment verification checks."""
        try:
            # Check service status
            status = await self.cmd.run_command("systemctl status cursor-listener")
            if "active (running)" not in status:
                raise RuntimeError("Service not running")
            
            # Check logs for errors
            logs = await self.cmd.run_command("journalctl -u cursor-listener -n 50")
            if "error" in logs.lower() or "exception" in logs.lower():
                raise RuntimeError("Errors found in service logs")
            
            # Verify metrics endpoint
            metrics = await self.cmd.run_command(
                f"curl -s localhost:{self.config['cursor']['metrics_port']}/-/healthy"
            )
            if "ok" not in metrics.lower():
                raise RuntimeError("Metrics endpoint not healthy")
            
            # Test file processing
            test_prompt = {
                "prompt_id": "deploy_test",
                "prompt_text": "Deployment verification",
                "source_agent": AGENT_ID
            }
            test_file = Path(self.config["cursor"]["pending_dir"]) / "deploy_test.json"
            test_file.write_text(json.dumps(test_prompt))
            
            # Wait for processing
            await asyncio.sleep(5)
            
            # Verify feedback
            feedback_files = list(Path(self.config["cursor"]["feedback_dir"]).glob("*.json"))
            if not feedback_files:
                raise RuntimeError("No feedback generated")
            
            log_event("DEPLOYMENT_VERIFIED", AGENT_ID, {"status": "success"})
            return True
            
        except Exception as e:
            log_event("VERIFICATION_FAILED", AGENT_ID, {"error": str(e)})
            return False

    async def deploy(self) -> bool:
        """Execute full deployment process."""
        steps = [
            (self.run_tests, "Test Execution"),
            (self.backup_existing, "Backup Creation"),
            (self.prepare_system, "System Preparation"),
            (self.deploy_service, "Service Deployment"),
            (self.verify_deployment, "Deployment Verification")
        ]
        
        for step_func, step_name in steps:
            log_event("STEP_STARTED", AGENT_ID, {"step": step_name})
            success = await step_func()
            
            if not success:
                log_event("DEPLOYMENT_ABORTED", AGENT_ID, {
                    "failed_step": step_name,
                    "status": "failure"
                })
                return False
                
        log_event("DEPLOYMENT_COMPLETED", AGENT_ID, {"status": "success"})
        return True

async def main():
    """Main deployment orchestration."""
    agent = DeploymentAgent()
    success = await agent.deploy()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 