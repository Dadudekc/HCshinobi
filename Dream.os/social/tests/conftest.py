"""Test configuration and shared fixtures."""

import os
import sys
import pytest

# Add project root to the Python path before tests are collected
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure asyncio for testing
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as an async test"
    )

# You can also define shared fixtures here if needed
# Example:
# @pytest.fixture(scope='session')
# def shared_resource():
#     print("\nSetting up shared resource")
#     yield "resource_data"
#     print("\nTearing down shared resource") 