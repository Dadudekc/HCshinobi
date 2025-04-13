"""
Quality Assurance Module

This module implements the quality assurance system for the project,
including testing frameworks, quality metrics, and validation processes.
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    """Status of a test case"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    PENDING = "pending"

class TestType(Enum):
    """Type of test case"""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USER_ACCEPTANCE = "user_acceptance"

class TestCase:
    """Represents a single test case"""
    def __init__(self, name: str, test_type: TestType, description: str):
        self.name = name
        self.test_type = test_type
        self.description = description
        self.status = TestStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.metrics: Dict[str, Any] = {}

    def start(self) -> None:
        """Start the test case"""
        self.start_time = datetime.now()
        self.status = TestStatus.PENDING
        logger.info(f"Starting test case: {self.name}")

    def complete(self, status: TestStatus, error_message: Optional[str] = None) -> None:
        """Complete the test case with given status"""
        self.end_time = datetime.now()
        self.status = status
        self.error_message = error_message
        logger.info(f"Completed test case: {self.name} with status: {status.value}")

    def add_metric(self, name: str, value: Any) -> None:
        """Add a metric to the test case"""
        self.metrics[name] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary"""
        return {
            "name": self.name,
            "test_type": self.test_type.value,
            "description": self.description,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "metrics": self.metrics
        }

class TestSuite:
    """Represents a collection of test cases"""
    def __init__(self, name: str):
        self.name = name
        self.test_cases: List[TestCase] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case to the suite"""
        self.test_cases.append(test_case)

    def start(self) -> None:
        """Start the test suite"""
        self.start_time = datetime.now()
        logger.info(f"Starting test suite: {self.name}")

    def complete(self) -> None:
        """Complete the test suite"""
        self.end_time = datetime.now()
        logger.info(f"Completed test suite: {self.name}")

    def get_status(self) -> TestStatus:
        """Get overall status of the test suite"""
        if not self.test_cases:
            return TestStatus.PENDING
        
        if any(test.status == TestStatus.FAILED for test in self.test_cases):
            return TestStatus.FAILED
        if any(test.status == TestStatus.ERROR for test in self.test_cases):
            return TestStatus.ERROR
        if all(test.status == TestStatus.PASSED for test in self.test_cases):
            return TestStatus.PASSED
        return TestStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """Convert test suite to dictionary"""
        return {
            "name": self.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.get_status().value,
            "test_cases": [test.to_dict() for test in self.test_cases]
        }

class QualityAssurance:
    """Main quality assurance system"""
    def __init__(self):
        self.test_suites: Dict[str, TestSuite] = {}
        self.quality_metrics: Dict[str, float] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def create_test_suite(self, name: str) -> TestSuite:
        """Create a new test suite"""
        if name in self.test_suites:
            raise ValueError(f"Test suite {name} already exists")
        
        suite = TestSuite(name)
        self.test_suites[name] = suite
        return suite

    def get_test_suite(self, name: str) -> Optional[TestSuite]:
        """Get a test suite by name"""
        return self.test_suites.get(name)

    def start_qa_process(self) -> None:
        """Start the QA process"""
        self.start_time = datetime.now()
        logger.info("Starting QA process")

    def complete_qa_process(self) -> None:
        """Complete the QA process"""
        self.end_time = datetime.now()
        logger.info("Completed QA process")

    def add_quality_metric(self, name: str, value: float) -> None:
        """Add a quality metric"""
        self.quality_metrics[name] = value

    def get_overall_status(self) -> TestStatus:
        """Get overall status of QA process"""
        if not self.test_suites:
            return TestStatus.PENDING
        
        suite_statuses = [suite.get_status() for suite in self.test_suites.values()]
        
        if TestStatus.FAILED in suite_statuses:
            return TestStatus.FAILED
        if TestStatus.ERROR in suite_statuses:
            return TestStatus.ERROR
        if all(status == TestStatus.PASSED for status in suite_statuses):
            return TestStatus.PASSED
        return TestStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """Convert QA system to dictionary"""
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.get_overall_status().value,
            "test_suites": {name: suite.to_dict() for name, suite in self.test_suites.items()},
            "quality_metrics": self.quality_metrics
        } 