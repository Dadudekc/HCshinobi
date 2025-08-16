#!/usr/bin/env python3
"""
Development Setup Script for HCshinobi
=====================================
Helps developers set up the environment and run tests
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def print_banner():
    """Print the HCshinobi development banner"""
    print("=" * 60)
    print("HCSHINOBI - DEVELOPMENT SETUP")
    print("=" * 60)
    print("Hardcore Naruto-themed MMO Discord Bot")
    print("Clan assignments, token economy, NPC management, AI-driven content")
    print("=" * 60)

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'discord', 'python-dotenv', 'aiohttp', 'dataclasses-json', 'aiofiles'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.lower().replace('-', '_'))
            print(f"✅ {package} - Installed")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Missing packages: {', '.join(missing_packages)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(".env")
    if not env_path.exists():
        print("⚠️  .env file not found")
        print("   Run: cp .env-example .env")
        print("   Then edit .env with your Discord bot credentials")
        return False
    
    print("✅ .env file found")
    
    # Check for required environment variables
    required_vars = [
        'DISCORD_BOT_TOKEN',
        'DISCORD_APPLICATION_ID', 
        'DISCORD_GUILD_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Please update your .env file")
        return False
    
    print("✅ All required environment variables set")
    return True

def run_tests(test_type="all"):
    """Run the test suite"""
    print(f"\n🧪 Running {test_type} tests...")
    
    if test_type == "unit":
        cmd = ["pytest", "tests/unit", "-v", "--cov=HCshinobi", "--cov-report=term-missing"]
    elif test_type == "integration":
        cmd = ["pytest", "tests/integration", "-v", "--cov=HCshinobi", "--cov-report=term-missing"]
    elif test_type == "e2e":
        cmd = ["pytest", "tests/e2e", "-v", "--cov=HCshinobi", "--cov-report=term-missing"]
    elif test_type == "battle":
        cmd = ["pytest", "tests/battle", "-v", "--cov=HCshinobi", "--cov-report=term-missing"]
    elif test_type == "mission":
        cmd = ["pytest", "tests/missions", "-v", "--cov=HCshinobi", "--cov-report=term-missing"]
    else:
        cmd = ["pytest", "tests", "-v", "--cov=HCshinobi", "--cov-report=term-missing"]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Tests completed successfully!")
        if result.stdout:
            print("\nTest Output:")
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        if e.stdout:
            print("\nSTDOUT:", e.stdout)
        if e.stderr:
            print("\nSTDERR:", e.stderr)
        return False
    
    return True

def check_code_quality():
    """Run code quality checks"""
    print("\n🔍 Running code quality checks...")
    
    # Check with flake8
    try:
        result = subprocess.run(["flake8", "HCshinobi", "tests"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Flake8 - No style issues found")
        else:
            print("⚠️  Flake8 - Style issues found:")
            print(result.stdout)
    except FileNotFoundError:
        print("⚠️  Flake8 not installed - skipping style check")
    
    # Check with black
    try:
        result = subprocess.run(["black", "--check", "HCshinobi", "tests"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Black - Code is properly formatted")
        else:
            print("⚠️  Black - Code formatting issues found")
            print("   Run: black HCshinobi tests")
    except FileNotFoundError:
        print("⚠️  Black not installed - skipping format check")
    
    # Check with mypy
    try:
        result = subprocess.run(["mypy", "HCshinobi"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ MyPy - No type issues found")
        else:
            print("⚠️  MyPy - Type issues found:")
            print(result.stdout)
    except FileNotFoundError:
        print("⚠️  MyPy not installed - skipping type check")

def setup_database():
    """Set up the SQLite database"""
    print("\n🗄️  Setting up database...")
    
    # Check if database files exist
    data_dir = Path("HCshinobi/data")
    if data_dir.exists():
        print("✅ Data directory exists")
        
        # Check for key data files
        key_files = ["characters.json", "clans.json", "missions.json"]
        for file in key_files:
            file_path = data_dir / file
            if file_path.exists():
                print(f"   ✅ {file} - Found")
            else:
                print(f"   ⚠️  {file} - Missing")
    else:
        print("📝 Creating data directory...")
        data_dir.mkdir(parents=True, exist_ok=True)
        print("   Data directory created")

def main():
    """Main development setup function"""
    parser = argparse.ArgumentParser(description="HCshinobi Development Setup")
    parser.add_argument("--tests", choices=["all", "unit", "integration", "e2e", "battle", "mission"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--quality", action="store_true", 
                       help="Run code quality checks")
    parser.add_argument("--setup", action="store_true", 
                       help="Set up development environment")
    parser.add_argument("--env-check", action="store_true",
                       help="Check environment configuration")
    
    args = parser.parse_args()
    
    print_banner()
    
    # Check environment
    if not check_python_version():
        return 1
    
    if not check_dependencies():
        return 1
    
    # Check environment file if requested
    if args.env_check:
        if not check_env_file():
            return 1
    
    # Setup if requested
    if args.setup:
        setup_database()
    
    # Run tests
    if not run_tests(args.tests):
        return 1
    
    # Run quality checks if requested
    if args.quality:
        check_code_quality()
    
    print("\n🎉 Development setup completed successfully!")
    print("\nNext steps:")
    print("1. Configure your .env file with Discord bot credentials")
    print("2. Run: python main.py")
    print("3. Check: HCshinobi/ for bot implementation")
    print("4. Read: tests/README.md for testing information")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
