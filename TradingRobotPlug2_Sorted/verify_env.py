#!/usr/bin/env python
"""
Environment verification script for the trading robot project.
This script checks if all required modules are installed and working.
"""

import sys
import importlib
import platform
from importlib.metadata import version
from importlib.metadata import PackageNotFoundError

def check_package(package_name):
    """Check if a package is installed and return its version."""
    try:
        importlib.import_module(package_name)
        try:
            ver = version(package_name)
            return f"✓ {package_name} (version {ver})"
        except PackageNotFoundError:
            return f"✓ {package_name} (not installed)"
        except Exception as e:
            return f"✓ {package_name} (version unknown: {str(e)})"
    except ImportError:
        return f"✗ {package_name} (NOT INSTALLED)"

def main():
    """Main verification function."""
    print("\n=== PYTHON ENVIRONMENT VERIFICATION ===\n")
    
    # Python version check
    py_version = sys.version.split()[0]
    print(f"Python version: {py_version}")
    print(f"Python executable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    
    print("\n--- Required Packages ---")
    
    # Core dependencies
    core_packages = ["pandas", "numpy", "yaml"]
    for package in core_packages:
        print(check_package(package))
    
    # Data source APIs
    api_packages = ["yfinance", "alpaca"]
    print("\n--- Data API Packages ---")
    for package in api_packages:
        print(check_package(package))
    
    # Testing packages
    test_packages = ["pytest", "pytest_asyncio"]
    print("\n--- Testing Packages ---")
    for package in test_packages:
        print(check_package(package))
    
    # Check trading_robot_plug package
    print("\n--- Project Package ---")
    try:
        import trading_robot_plug
        print("✓ trading_robot_plug package is installed")
        
        # Try importing fetchers
        from trading_robot_plug.data.fetchers.base_fetcher import BaseFetcher
        from trading_robot_plug.data.fetchers.yahoo_finance_fetcher import YahooFinanceFetcher
        from trading_robot_plug.data.fetchers.fetcher_factory import FetcherFactory
        
        print("✓ Fetcher modules imported successfully")
    except ImportError as e:
        print(f"✗ Error importing trading_robot_plug package: {e}")
    
    print("\n=== VERIFICATION COMPLETE ===\n")
    
    # Final result
    if all(package in ''.join(sys.modules.keys()) for package in 
           ["pandas", "numpy", "yfinance", "trading_robot_plug"]):
        print("Environment appears to be correctly set up!")
    else:
        print("Some required packages are missing. Please check the output above.")

if __name__ == "__main__":
    main() 