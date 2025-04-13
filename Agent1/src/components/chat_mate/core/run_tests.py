"""
Test runner script for Instagram strategy tests
"""

import unittest
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_tests():
    """Run all Instagram strategy tests"""
    # Add the parent directory to the Python path
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
        
    # Discover and load all test cases
    loader = unittest.TestLoader()
    start_dir = str(Path(__file__).parent)
    
    # Load unit tests
    unit_tests = loader.discover(
        start_dir,
        pattern='test_instagram_strategy.py'
    )
    
    # Load integration tests
    integration_tests = loader.discover(
        start_dir,
        pattern='test_instagram_strategy_integration.py'
    )
    
    # Create test suites
    unit_suite = unittest.TestSuite(unit_tests)
    integration_suite = unittest.TestSuite(integration_tests)
    
    # Run unit tests
    logger.info("Running unit tests...")
    unit_runner = unittest.TextTestRunner(verbosity=2)
    unit_result = unit_runner.run(unit_suite)
    
    # Run integration tests
    logger.info("\nRunning integration tests...")
    integration_runner = unittest.TextTestRunner(verbosity=2)
    integration_result = integration_runner.run(integration_suite)
    
    # Print summary
    logger.info("\nTest Summary:")
    logger.info(f"Unit Tests: {unit_result.testsRun} tests run")
    logger.info(f"Unit Tests Failed: {len(unit_result.failures)}")
    logger.info(f"Unit Tests Errors: {len(unit_result.errors)}")
    
    logger.info(f"\nIntegration Tests: {integration_result.testsRun} tests run")
    logger.info(f"Integration Tests Failed: {len(integration_result.failures)}")
    logger.info(f"Integration Tests Errors: {len(integration_result.errors)}")
    
    # Return appropriate exit code
    if unit_result.wasSuccessful() and integration_result.wasSuccessful():
        return 0
    return 1

if __name__ == '__main__':
    sys.exit(run_tests()) 