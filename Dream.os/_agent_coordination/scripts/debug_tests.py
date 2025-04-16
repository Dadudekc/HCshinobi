"""Debug-focused test runner for Cursor Result Listener tests."""

import asyncio
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest
from _pytest.config import Config
from _pytest.main import Session
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo

from core.feedback import log_event

AGENT_ID = "TestDebugAgent"
DEBUG_LOG_DIR = Path("logs/test_debug")

class TestDebugPlugin:
    """Pytest plugin for detailed test debugging and analysis."""
    
    def __init__(self):
        self.failed_tests: List[Dict] = []
        self.slow_tests: List[Dict] = []
        self.flaky_tests: List[Dict] = []
        self.start_time = datetime.now()
        self.debug_data: Dict = {}
        
    def pytest_sessionstart(self, session: Session):
        """Set up debug environment at start of test session."""
        DEBUG_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.debug_log = DEBUG_LOG_DIR / f"debug_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        
        log_event("DEBUG_SESSION_STARTED", AGENT_ID, {
            "timestamp": self.start_time.isoformat(),
            "python_version": sys.version,
            "pytest_version": pytest.__version__
        })

    def pytest_runtest_protocol(self, item: Item, nextitem: Optional[Item]):
        """Track test execution and capture detailed context."""
        test_id = item.nodeid
        self.debug_data[test_id] = {
            "start_time": datetime.now().isoformat(),
            "fixtures": [f.name for f in item.fixturenames],
            "markers": [m.name for m in item.iter_markers()],
            "file": str(item.fspath),
            "line": item.lineno,
        }

    def pytest_runtest_logreport(self, report: TestReport):
        """Process test results and collect debug information."""
        if report.when != "call":
            return
            
        test_id = report.nodeid
        duration = report.duration
        
        # Track slow tests (>1s)
        if duration > 1.0:
            self.slow_tests.append({
                "test_id": test_id,
                "duration": duration,
                "context": self.debug_data.get(test_id, {})
            })

        if report.failed:
            # Capture detailed failure information
            failure_data = {
                "test_id": test_id,
                "duration": duration,
                "error_type": report.longrepr.reprcrash.message if hasattr(report.longrepr, 'reprcrash') else str(report.longrepr),
                "traceback": report.longreprtext,
                "context": self.debug_data.get(test_id, {}),
            }
            
            self.failed_tests.append(failure_data)
            
            # Log failure event
            log_event("TEST_FAILURE", AGENT_ID, {
                "test_id": test_id,
                "error_type": failure_data["error_type"]
            })

    def pytest_sessionfinish(self, session: Session, exitstatus: int):
        """Generate comprehensive debug report."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        debug_report = {
            "summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration,
                "total_tests": session.testscollected,
                "failed_tests": len(self.failed_tests),
                "slow_tests": len(self.slow_tests),
                "flaky_tests": len(self.flaky_tests),
                "exit_status": exitstatus
            },
            "failed_tests": self.failed_tests,
            "slow_tests": self.slow_tests,
            "flaky_tests": self.flaky_tests,
            "environment": {
                "python_version": sys.version,
                "pytest_version": pytest.__version__,
                "os": os.name,
                "platform": sys.platform
            }
        }
        
        # Write detailed debug report
        debug_report_path = DEBUG_LOG_DIR / f"report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        debug_report_path.write_text(json.dumps(debug_report, indent=2))
        
        # Log completion event
        log_event("DEBUG_SESSION_COMPLETED", AGENT_ID, {
            "duration": duration,
            "failed_tests": len(self.failed_tests),
            "report_path": str(debug_report_path)
        })
        
        # Print summary to console
        self._print_debug_summary(debug_report)

    def _print_debug_summary(self, report: Dict):
        """Print formatted debug summary to console."""
        print("\n" + "="*80)
        print("🔍 TEST DEBUG SUMMARY")
        print("="*80)
        
        print(f"\n⏱  Duration: {report['summary']['duration']:.2f}s")
        print(f"📊 Total Tests: {report['summary']['total_tests']}")
        print(f"❌ Failed Tests: {report['summary']['failed_tests']}")
        print(f"🐌 Slow Tests: {len(report['slow_tests'])}")
        print(f"🔄 Flaky Tests: {len(report['flaky_tests'])}")
        
        if report['failed_tests']:
            print("\n❌ FAILED TESTS")
            print("-"*80)
            for test in report['failed_tests']:
                print(f"\n🔴 {test['test_id']}")
                print(f"   Error: {test['error_type']}")
                print(f"   Duration: {test['duration']:.2f}s")
                
        if report['slow_tests']:
            print("\n🐌 SLOW TESTS")
            print("-"*80)
            for test in report['slow_tests']:
                print(f"\n⏱  {test['test_id']}")
                print(f"   Duration: {test['duration']:.2f}s")
                
        print("\n" + "="*80)
        print(f"📝 Detailed report: {DEBUG_LOG_DIR}/report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json")
        print("="*80 + "\n")

async def run_debug_tests():
    """Run tests with debug plugin and analysis."""
    debug_plugin = TestDebugPlugin()
    
    args = [
        "tests/tools/test_cursor_result_listener.py",
        "-v",
        "--tb=short",
        "-l",
        "--cov=tools.cursor_result_listener",
        "--cov-report=html",
        "-n", "auto"  # Parallel execution
    ]
    
    exit_code = pytest.main(args, plugins=[debug_plugin])
    
    return exit_code == 0

async def main():
    """Main debug execution."""
    try:
        success = await run_debug_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        log_event("DEBUG_SESSION_ERROR", AGENT_ID, {
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 