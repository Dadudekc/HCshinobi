"""Handles pre-shutdown diagnostic checks for the Agent Bus system."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Callable

from .bus_types import AgentStatus
from .agent_registry import AgentRegistry
from core.coordination.dispatcher import EventDispatcher, EventType # Assuming dispatcher is accessible
from core.utils.system import SystemUtils # Assuming utils are accessible
# from core.utils.file_manager import FileManager # FileManager not used directly in these checks

logger = logging.getLogger(__name__)

class SystemDiagnostics:
    """Performs various health checks before system shutdown."""

    def __init__(self,
                 agent_registry: AgentRegistry,
                 event_dispatcher: EventDispatcher,
                 sys_utils: SystemUtils,
                 dispatch_event_callback: Callable):
        self.agent_registry = agent_registry
        self.event_dispatcher = event_dispatcher
        self.sys_utils = sys_utils
        self._dispatch_event = dispatch_event_callback

    async def run_pre_shutdown_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive pre-shutdown diagnostics."""
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "total_passed": 0,
            "total_failed": 0,
            "critical_warnings": []
        }

        checks_to_run = {
            "agent_status": self._check_agent_status,
            "state_files": self._check_state_files,
            "resources": self._check_resources,
            "event_system": self._check_event_system
        }

        for check_name, check_func in checks_to_run.items():
            try:
                check_result = await check_func()
                diagnostics["checks"][check_name] = check_result
                if check_result["passed"]:
                    diagnostics["total_passed"] += 1
                else:
                    diagnostics["total_failed"] += 1
                    if check_result.get("critical"):
                        # Ensure errors are strings
                        errors_str = [str(e) for e in check_result.get("errors", [])]
                        diagnostics["critical_warnings"].extend(errors_str)
            except Exception as e:
                logger.error(f"Diagnostic check '{check_name}' failed: {e}", exc_info=True)
                error_result = {
                    "passed": False,
                    "errors": [f"Check '{check_name}' failed unexpectedly: {str(e)}"],
                    "critical": True,
                    "details": {}
                }
                diagnostics["checks"][check_name] = error_result
                diagnostics["total_failed"] += 1
                diagnostics["critical_warnings"].append(error_result["errors"][0])

        # Log final diagnostics via callback
        status = "ready_for_shutdown" if diagnostics["total_failed"] == 0 else "errors_detected"
        await self._dispatch_event(
            "pre_shutdown_check",
            {
                "status": status,
                "diagnostics": diagnostics
            },
            priority=0 # Assuming priority convention
        )

        return diagnostics

    def _validate_state_file(self, file_name: str, data: Any) -> bool:
        """Validate state file format and required fields. Basic check for now."""
        if file_name == "task_list.json":
            required = {"task_id", "status", "priority"}
        elif file_name == "mailbox.json":
            required = {"agent_id", "status", "pending_operations"}
        else:
            # For simplicity, assume other files are valid if they load
            logger.debug(f"No specific validation rules for {file_name}")
            return True 
            
        if isinstance(data, list):
            if not data: return True # Empty list is valid
            return all(isinstance(item, dict) and required.issubset(item.keys()) for item in data)
        elif isinstance(data, dict):
             return required.issubset(data.keys())
        else:
            logger.warning(f"Unexpected data type for state file {file_name}: {type(data)}")
            return False

    async def _check_agent_status(self) -> Dict[str, Any]:
        """Check status of all agents via AgentRegistry."""
        result = {
            "passed": True,
            "errors": [],
            "critical": False,
            "details": {}
        }
        try:
            agents_info = await self.agent_registry.get_all_agents()
            active_agents = await self.agent_registry.get_active_agents_set()

            for agent_id, info in agents_info.items():
                agent_status_details = {
                    "reported_status": info.get("status", "unknown"),
                    "has_mailbox": False,
                    "mailbox_valid": False,
                    "has_task_list": False,
                    "task_list_valid": False,
                    "errors": []
                }

                # Base path for agent memory
                agent_memory_path = Path(f"memory/agents/{agent_id}")

                # Check mailbox.json
                mailbox_path = agent_memory_path / "mailbox.json"
                if mailbox_path.exists():
                    agent_status_details["has_mailbox"] = True
                    try:
                        content = mailbox_path.read_text()
                        if content.strip(): # Check if file is not empty
                            mailbox_data = json.loads(content)
                            if self._validate_state_file("mailbox.json", mailbox_data):
                                agent_status_details["mailbox_valid"] = True
                            else:
                                agent_status_details["errors"].append("mailbox.json format invalid")
                        else:
                             agent_status_details["errors"].append("mailbox.json is empty") 
                    except json.JSONDecodeError:
                        agent_status_details["errors"].append("mailbox.json is not valid JSON")
                    except Exception as e:
                        agent_status_details["errors"].append(f"Error reading mailbox.json: {str(e)}")
                else:
                    agent_status_details["errors"].append("Missing mailbox.json")

                # Check task_list.json
                task_path = agent_memory_path / "task_list.json"
                if task_path.exists():
                    agent_status_details["has_task_list"] = True
                    try:
                        content = task_path.read_text()
                        if content.strip(): # Check if file is not empty
                            task_data = json.loads(content)
                            if self._validate_state_file("task_list.json", task_data):
                                agent_status_details["task_list_valid"] = True
                            else:
                                agent_status_details["errors"].append("task_list.json format invalid")
                        else:
                            agent_status_details["errors"].append("task_list.json is empty")
                    except json.JSONDecodeError:
                        agent_status_details["errors"].append("task_list.json is not valid JSON")
                    except Exception as e:
                        agent_status_details["errors"].append(f"Error reading task_list.json: {str(e)}")
                else:
                    agent_status_details["errors"].append("Missing task_list.json")

                # Check for error state reported by the registry
                if info.get("status") == AgentStatus.ERROR.value:
                    error_msg = info.get('error_message', 'No details provided')
                    agent_status_details["errors"].append(f"Agent in ERROR state: {error_msg}")

                result["details"][agent_id] = agent_status_details
                if agent_status_details["errors"]:
                    result["passed"] = False
                    result["errors"].extend([f"[{agent_id}] {err}" for err in agent_status_details["errors"]])

            # Critical if any active agent has errors
            if not result["passed"]:
                result["critical"] = any(
                    agent_id in active_agents and result["details"].get(agent_id, {}).get("errors")
                    for agent_id in agents_info
                )

        except Exception as e:
            logger.error(f"Agent status check failed unexpectedly: {e}", exc_info=True)
            result["passed"] = False
            result["errors"].append(f"Agent status check failed: {str(e)}")
            result["critical"] = True
            
        return result

    async def _check_state_files(self) -> Dict[str, Any]:
        """Check critical system directories."""
        result = {
            "passed": True,
            "errors": [],
            "critical": False,
            "details": {}
        }
        required_dirs = ["memory", "logs", "config", "temp", "memory/agents"]
        for dir_name in required_dirs:
            path = Path(dir_name)
            dir_status = {"exists": False, "is_dir": False, "writable": False, "error": None}
            try:
                if not path.exists():
                    result["errors"].append(f"Missing required directory: {dir_name}")
                    dir_status["error"] = "Does not exist"
                elif not path.is_dir():
                    result["errors"].append(f"Path exists but is not a directory: {dir_name}")
                    dir_status["exists"] = True
                    dir_status["error"] = "Not a directory"
                else:
                    dir_status["exists"] = True
                    dir_status["is_dir"] = True
                    try:
                        # Test write access
                        test_file = path / ".write_test"
                        test_file.write_text("test")
                        test_file.unlink()
                        dir_status["writable"] = True
                    except Exception as write_e:
                        dir_status["error"] = f"Write test failed: {str(write_e)}"
                        result["errors"].append(f"Directory not writable: {dir_name} ({str(write_e)})")
            except Exception as e:
                dir_status["error"] = f"Error checking directory: {str(e)}"
                result["errors"].append(f"Directory check failed: {dir_name} ({str(e)})")
            result["details"][dir_name] = dir_status

        return result 