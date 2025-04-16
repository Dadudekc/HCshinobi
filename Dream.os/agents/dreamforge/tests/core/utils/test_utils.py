"""Shared test utilities for dreamforge tests."""
import os
import sys
import json
import pytest
import logging
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from typing import Dict, List, Optional
from dreamforge.core.memory.governance_memory_engine import log_event

logger = logging.getLogger(__name__)

def setup_test_imports():
    """Add project root to sys.path for test imports."""
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

def init_test_suite(suite_name: str, test_count: int, test_categories: list[str]):
    """Initialize test suite with consistent logging."""
    log_event("TEST_SUITE_INITIALIZED", suite_name, {
        "test_count": test_count,
        "test_categories": test_categories,
        "timestamp": datetime.now().isoformat()
    })

def validate_agent_files(agent_id: str, required_files: List[str] = None) -> Dict[str, bool]:
    """Validate that an agent has all required files."""
    if required_files is None:
        required_files = ['mailbox.json', 'task_list.json']
    
    agent_dir = Path(f"memory/agents/{agent_id}")
    results = {}
    
    for file in required_files:
        file_path = agent_dir / file
        results[file] = file_path.exists() and file_path.stat().st_size > 0
    
    return results

def cleanup_stale_test_files(max_age_days: int = 30) -> int:
    """Remove test files older than specified days."""
    cleaned = 0
    test_dirs = ['memory/test', 'logs/test']
    
    for dir_path in test_dirs:
        if not os.path.exists(dir_path):
            continue
            
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_age > timedelta(days=max_age_days):
                    try:
                        os.remove(file_path)
                        cleaned += 1
                    except OSError as e:
                        logger.warning(f"Failed to remove stale file {file_path}: {e}")
    
    return cleaned

def check_system_health() -> Dict[str, Dict[str, any]]:
    """Perform comprehensive system health check."""
    results = {
        "directories": {
            "status": "pass",
            "details": [],
            "errors": []
        },
        "agent_files": {
            "status": "pass",
            "details": [],
            "errors": []
        },
        "task_system": {
            "status": "pass",
            "details": [],
            "errors": []
        }
    }
    
    # Check critical directories
    critical_dirs = ['memory', 'logs', 'config', 'memory/agents', 'memory/test']
    for dir_path in critical_dirs:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            test_file = Path(dir_path) / '.test_write'
            test_file.write_text('test')
            test_file.unlink()
            results["directories"]["details"].append(f"Directory {dir_path} is writable")
        except Exception as e:
            results["directories"]["status"] = "fail"
            results["directories"]["errors"].append(f"Failed to access {dir_path}: {str(e)}")
    
    # Check agent files
    agent_ids = ['workflow_agent', 'planner_agent', 'cursor_agent']
    for agent_id in agent_ids:
        validation = validate_agent_files(agent_id)
        if all(validation.values()):
            results["agent_files"]["details"].append(f"Agent {agent_id} files validated")
        else:
            results["agent_files"]["status"] = "fail"
            missing = [f for f, exists in validation.items() if not exists]
            results["agent_files"]["errors"].append(f"Agent {agent_id} missing files: {missing}")
    
    # Log final health check
    status = "ready_for_shutdown" if all(r["status"] == "pass" for r in results.values()) else "errors_detected"
    log_event("pre_shutdown_check", "system_health", {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "passing_checks": sum(1 for r in results.values() if r["status"] == "pass"),
        "failing_checks": sum(1 for r in results.values() if r["status"] == "fail"),
        "details": results
    })
    
    return results

@pytest.fixture
def mock_agent_bus():
    """Provides a mock agent bus instance for testing."""
    mock_bus = MagicMock()
    mock_bus.dispatch = MagicMock(return_value="Step Result")
    return mock_bus

@pytest.fixture
def temp_workspace(tmp_path):
    """Creates a temporary workspace directory for testing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return str(workspace)

@pytest.fixture
def cleanup_test_env():
    """Fixture to clean up test environment before and after tests."""
    # Setup
    cleanup_stale_test_files()
    
    yield
    
    # Teardown
    cleanup_stale_test_files()
    check_system_health()

if __name__ == "__main__":
    # Example usage: Run & Debug
    import time
    from pprint import pprint
    
    def run_system_validation():
        """Demonstrate test utilities capabilities with a full system validation."""
        print("\n=== Dream.OS Test Utilities Demo ===\n")
        
        # 1. Setup Test Environment
        print("1. Setting up test environment...")
        setup_test_imports()
        init_test_suite("TestUtilsDemo", test_count=3, test_categories=["health", "cleanup", "validation"])
        print("✓ Test environment initialized\n")
        
        # 2. Create Test Files
        print("2. Creating test files...")
        test_dir = Path("memory/test")
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create some test files with different ages
        for i in range(3):
            file_path = test_dir / f"test_file_{i}.json"
            file_path.write_text(json.dumps({"test": f"data_{i}"}))
            # Modify access time to simulate old files
            os.utime(file_path, (time.time() - (i * 40 * 24 * 3600), time.time() - (i * 40 * 24 * 3600)))
        print("✓ Test files created\n")
        
        # 3. Validate Agent Files
        print("3. Checking agent files...")
        agent_results = validate_agent_files("workflow_agent")
        print("Agent file validation results:")
        pprint(agent_results)
        print()
        
        # 4. Clean Stale Files
        print("4. Cleaning stale test files...")
        cleaned_count = cleanup_stale_test_files(max_age_days=30)
        print(f"✓ Removed {cleaned_count} stale files\n")
        
        # 5. Full System Health Check
        print("5. Running system health check...")
        health_results = check_system_health()
        print("\nHealth Check Results:")
        pprint(health_results)
        
        # 6. Summary
        print("\n=== Validation Summary ===")
        status = "ready_for_shutdown" if all(r["status"] == "pass" for r in health_results.values()) else "errors_detected"
        print(f"System Status: {status}")
        print(f"Passing Checks: {sum(1 for r in health_results.values() if r['status'] == 'pass')}")
        print(f"Failing Checks: {sum(1 for r in health_results.values() if r['status'] == 'fail')}")
    
    try:
        run_system_validation()
    except Exception as e:
        print(f"\n❌ Error during validation: {str(e)}")
        raise
    else:
        print("\n✅ Validation completed successfully") 