"""
HCShinobi Beta Verification Script
This script performs comprehensive verification of the HCShinobi bot's components,
environment setup, and integration points.
"""

import asyncio
import json
import logging
import os
import sys
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import discord
from dotenv import load_dotenv
import aiohttp
import sqlite3
import importlib.util

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('verification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('beta_verification')

class VerificationResult:
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.message = ""
        self.details: Dict[str, Any] = {}
        self.timestamp = datetime.now().isoformat()
        self.error: Optional[Exception] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "success": self.success,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "error": str(self.error) if self.error else None
        }

class BetaVerifier:
    def __init__(self):
        self.results: List[VerificationResult] = []
        self.base_dir = Path(__file__).parent
        self.config_dir = self.base_dir / "config"
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"
        self.reports_dir = self.base_dir / "reports"

    async def verify_all(self) -> Dict[str, Any]:
        """Run all verification checks."""
        logger.info("Starting comprehensive beta verification...")
        
        # Environment verification
        await self.verify_environment()
        
        # Core components verification
        await self.verify_core_components()
        
        # Integration points verification
        await self.verify_integration_points()
        
        # Generate and save report
        report = self.generate_report()
        self.save_report(report)
        
        return report

    async def verify_environment(self):
        """Verify environment setup and requirements."""
        logger.info("Verifying environment setup...")
        
        # Check Python version
        result = VerificationResult("Python Version")
        try:
            version = platform.python_version()
            # Accept Python 3.8 or higher
            result.success = tuple(map(int, version.split('.'))) >= (3, 8)
            result.message = f"Python version: {version}"
            result.details = {
                "version": version,
                "required_version": "3.8+",
                "is_compatible": result.success
            }
        except Exception as e:
            result.error = e
            result.message = f"Error checking Python version: {str(e)}"
        self.results.append(result)

        # Check required directories
        result = VerificationResult("Directory Structure")
        try:
            required_dirs = [
                self.config_dir,
                self.data_dir,
                self.logs_dir,
                self.reports_dir,
                self.data_dir / "database",
                self.data_dir / "characters",
                self.data_dir / "clans",
                self.data_dir / "missions"
            ]
            missing_dirs = [d for d in required_dirs if not d.exists()]
            result.success = len(missing_dirs) == 0
            result.message = "All required directories exist" if result.success else f"Missing directories: {missing_dirs}"
            result.details = {
                "missing_dirs": [str(d) for d in missing_dirs],
                "required_dirs": [str(d) for d in required_dirs]
            }
        except Exception as e:
            result.error = e
            result.message = f"Error checking directories: {str(e)}"
        self.results.append(result)

        # Check environment variables
        result = VerificationResult("Environment Variables")
        try:
            load_dotenv()
            required_vars = [
                "DISCORD_TOKEN",
                "OPENAI_API_KEY",
                "OLLAMA_API_URL"
            ]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            result.success = len(missing_vars) == 0
            result.message = "All required environment variables are set" if result.success else f"Missing variables: {missing_vars}"
            result.details = {
                "missing_vars": missing_vars,
                "required_vars": required_vars,
                "env_file_exists": Path(".env").exists()
            }
        except Exception as e:
            result.error = e
            result.message = f"Error checking environment variables: {str(e)}"
        self.results.append(result)

    async def verify_core_components(self):
        """Verify core bot components."""
        logger.info("Verifying core components...")
        
        # Check database connection
        result = VerificationResult("Database Connection")
        try:
            db_path = self.data_dir / "database" / "dashboard.db"
            if not db_path.exists():
                raise FileNotFoundError(f"Database file not found: {db_path}")
                
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            result.success = True
            result.message = f"Successfully connected to database. Found {len(tables)} tables."
            result.details = {
                "tables": [table[0] for table in tables],
                "db_path": str(db_path),
                "db_exists": db_path.exists()
            }
        except Exception as e:
            result.error = e
            result.message = f"Database connection error: {str(e)}"
        self.results.append(result)

        # Check core modules
        result = VerificationResult("Core Modules")
        try:
            required_modules = [
                "HCshinobi.bot.bot",
                "HCshinobi.core.character_system",
                "HCshinobi.core.training_system",
                "HCshinobi.core.mission_system",
                "HCshinobi.core.clan_data"
            ]
            missing_modules = []
            for module in required_modules:
                if not importlib.util.find_spec(module):
                    missing_modules.append(module)
            
            result.success = len(missing_modules) == 0
            result.message = "All core modules are available" if result.success else f"Missing modules: {missing_modules}"
            result.details = {
                "missing_modules": missing_modules,
                "required_modules": required_modules,
                "python_path": sys.path
            }
        except Exception as e:
            result.error = e
            result.message = f"Error checking core modules: {str(e)}"
        self.results.append(result)

    async def verify_integration_points(self):
        """Verify external integrations and services."""
        logger.info("Verifying integration points...")
        
        # Check Discord connection
        result = VerificationResult("Discord Connection")
        try:
            token = os.getenv("DISCORD_TOKEN")
            if not token:
                raise ValueError("Discord token not found in environment variables")
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bot {token}"}
                async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result.success = True
                        result.message = f"Successfully connected to Discord as {data['username']}"
                        result.details = {
                            "bot_id": data["id"],
                            "bot_name": data["username"],
                            "bot_discriminator": data.get("discriminator", "0")
                        }
                    else:
                        error_data = await resp.json()
                        result.message = f"Discord API error: {resp.status} - {error_data.get('message', 'Unknown error')}"
                        result.details = {"status_code": resp.status, "error": error_data}
        except Exception as e:
            result.error = e
            result.message = f"Discord connection error: {str(e)}"
        self.results.append(result)

        # Check OpenAI integration
        result = VerificationResult("OpenAI Integration")
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found in environment variables")
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get("https://api.openai.com/v1/models", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result.success = True
                        result.message = "Successfully connected to OpenAI API"
                        result.details = {
                            "available_models": len(data.get("data", [])),
                            "organization": data.get("organization", "Unknown")
                        }
                    else:
                        error_data = await resp.json()
                        result.message = f"OpenAI API error: {resp.status} - {error_data.get('error', {}).get('message', 'Unknown error')}"
                        result.details = {"status_code": resp.status, "error": error_data}
        except Exception as e:
            result.error = e
            result.message = f"OpenAI integration error: {str(e)}"
        self.results.append(result)

        # Check Ollama integration
        result = VerificationResult("Ollama Integration")
        try:
            ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ollama_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result.success = True
                        result.message = "Successfully connected to Ollama API"
                        result.details = {
                            "available_models": len(data.get("models", [])),
                            "ollama_url": ollama_url
                        }
                    else:
                        error_data = await resp.json()
                        result.message = f"Ollama API error: {resp.status} - {error_data.get('error', 'Unknown error')}"
                        result.details = {"status_code": resp.status, "error": error_data}
        except Exception as e:
            result.error = e
            result.message = f"Ollama integration error: {str(e)}"
        self.results.append(result)

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive verification report."""
        total_checks = len(self.results)
        successful_checks = sum(1 for r in self.results if r.success)
        success_rate = (successful_checks / total_checks) * 100 if total_checks > 0 else 0

        # Group results by category
        categories = {
            "Environment": [r for r in self.results if r.name in ["Python Version", "Directory Structure", "Environment Variables"]],
            "Core Components": [r for r in self.results if r.name in ["Database Connection", "Core Modules"]],
            "Integrations": [r for r in self.results if r.name in ["Discord Connection", "OpenAI Integration", "Ollama Integration"]]
        }

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "failed_checks": total_checks - successful_checks,
                "success_rate": f"{success_rate:.2f}%",
                "categories": {
                    name: {
                        "total": len(results),
                        "successful": sum(1 for r in results if r.success),
                        "failed": sum(1 for r in results if not r.success)
                    }
                    for name, results in categories.items()
                }
            },
            "results": [r.to_dict() for r in self.results]
        }

        return report

    def save_report(self, report: Dict[str, Any]):
        """Save the verification report to file."""
        try:
            self.reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.reports_dir / f"verification_report_{timestamp}.json"
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Verification report saved to {report_path}")
            
            # Print detailed summary to console
            print("\n=== Verification Summary ===")
            print(f"Total Checks: {report['summary']['total_checks']}")
            print(f"Successful: {report['summary']['successful_checks']}")
            print(f"Failed: {report['summary']['failed_checks']}")
            print(f"Success Rate: {report['summary']['success_rate']}")
            print("\nCategory Breakdown:")
            for category, stats in report['summary']['categories'].items():
                print(f"\n{category}:")
                print(f"  Total: {stats['total']}")
                print(f"  Successful: {stats['successful']}")
                print(f"  Failed: {stats['failed']}")
            print("\nFailed Checks:")
            for result in report['results']:
                if not result['success']:
                    print(f"\n{result['name']}:")
                    print(f"  Error: {result['message']}")
                    if result.get('error'):
                        print(f"  Details: {result['error']}")
            print("\n==========================\n")
            
        except Exception as e:
            logger.error(f"Error saving verification report: {str(e)}")

async def main():
    """Main entry point for the verification script."""
    verifier = BetaVerifier()
    await verifier.verify_all()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nVerification interrupted by user.")
    except Exception as e:
        logger.error(f"Verification failed with error: {str(e)}", exc_info=True)
        sys.exit(1) 