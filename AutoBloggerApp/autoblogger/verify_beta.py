#!/usr/bin/env python3
"""
AutoBlogger Beta Verification Script

This script performs comprehensive checks to verify that AutoBlogger is ready for beta release.
It validates:
- Environment configuration
- Project structure
- Code quality
- Test coverage
- Documentation
- Dependencies

The script generates both human-readable Markdown reports and machine-friendly JSON output.
"""

import os
import json
import subprocess
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Set
import ast

# Configure logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / f"verify_beta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Required environment variables for API integrations
REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "WORDPRESS_URL",
    "WORDPRESS_USER",
    "WORDPRESS_PASS",
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "LINKEDIN_CLIENT_ID",
    "LINKEDIN_CLIENT_SECRET",
]

# Expected project structure
PROJECT_STRUCTURE = {
    "files": [
        "main.py",
        "main_window.py",
        "requirements.txt",
        ".env.example",
        "README.md",
        "LICENSE",
        "setup.py",
    ],
    "dirs": [
        "models",
        "services",
        "utils",
        "tests",
        "docs",
    ],
}


@dataclass
class CheckResult:
    """
    Represents the result of a single verification check.

    Attributes:
        name: Name of the check
        status: Whether the check passed
        details: Detailed explanation of the result
        recommendations: List of recommendations if check failed
    """

    name: str
    status: bool
    details: str = ""
    recommendations: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the check result to a dictionary."""
        return asdict(self)


@dataclass
class FileAnalysis:
    """Represents the analysis results for a single file."""

    has_docstring: bool = False
    has_type_hints: bool = False
    has_error_handling: bool = False
    complexity: int = 0
    test_coverage: float = 0.0
    issues: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class AutoBloggerVerifier:
    """
    Main class for verifying AutoBlogger's beta readiness.

    This class performs various checks on the project structure, code quality,
    and configuration to ensure everything is ready for beta release.
    """

    def __init__(self, project_root: str):
        """
        Initialize the verifier.

        Args:
            project_root: Base path of the project (defaults to current directory)
        """
        self.project_root = Path(project_root)
        self.results: List[CheckResult] = []
        self.analysis_results: Dict[str, FileAnalysis] = {}
        self.required_files = {
            "README.md",
            "requirements.txt",
            "setup.py",
            "LICENSE",
            "docs/",
            "tests/",
        }

    def check_env_files(self) -> CheckResult:
        """
        Check for presence of environment configuration files.

        Returns:
            CheckResult indicating whether .env and .env.example exist
        """
        try:
            missing = []
            for fn in (".env.example", ".env"):
                if not (self.project_root / fn).exists():
                    missing.append(fn)
            if missing:
                return CheckResult(
                    name="Env files",
                    status=False,
                    details=f"Missing: {', '.join(missing)}",
                    recommendations=["Add the missing .env / .env.example files"],
                )
            return CheckResult(
                name="Env files",
                status=True,
                details="Found both .env and .env.example",
            )
        except Exception as e:
            logger.error(f"Error checking env files: {e}")
            return CheckResult(
                name="Env files",
                status=False,
                details=f"Error: {str(e)}",
                recommendations=["Check file permissions and disk space"],
            )

    def check_env_vars(self) -> CheckResult:
        """
        Verify presence of required environment variables.

        Returns:
            CheckResult indicating whether all required variables are present
        """
        try:
            env_path = self.project_root / ".env"
            missing = []
            if not env_path.exists():
                return CheckResult(
                    name="Env variables",
                    status=False,
                    details=".env not found",
                    recommendations=["Create .env from .env.example"],
                )
            with open(env_path) as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            present = {l.split("=", 1)[0] for l in lines if "=" in l}
            for key in REQUIRED_ENV_VARS:
                if key not in present:
                    missing.append(key)
            if missing:
                return CheckResult(
                    name="Env variables",
                    status=False,
                    details=f"Missing keys: {', '.join(missing)}",
                    recommendations=["Populate .env with required API credentials"],
                )
            return CheckResult(
                name="Env variables", status=True, details="All required keys present"
            )
        except Exception as e:
            logger.error(f"Error checking env variables: {e}")
            return CheckResult(
                name="Env variables",
                status=False,
                details=f"Error: {str(e)}",
                recommendations=["Check .env file format and permissions"],
            )

    def check_requirements(self) -> CheckResult:
        """
        Verify requirements.txt exists and is properly formatted.

        Returns:
            CheckResult indicating whether requirements.txt is valid
        """
        try:
            req = self.project_root / "requirements.txt"
            if not req.exists():
                return CheckResult(
                    name="Requirements",
                    status=False,
                    details="requirements.txt not found",
                    recommendations=["Add requirements.txt listing your dependencies"],
                )
            if req.stat().st_size == 0:
                return CheckResult(
                    name="Requirements",
                    status=False,
                    details="requirements.txt is empty",
                    recommendations=["Populate requirements.txt via pip freeze"],
                )
            return CheckResult(
                name="Requirements", status=True, details="requirements.txt OK"
            )
        except Exception as e:
            logger.error(f"Error checking requirements: {e}")
            return CheckResult(
                name="Requirements",
                status=False,
                details=f"Error: {str(e)}",
                recommendations=["Check file permissions and format"],
            )

    def check_structure(self) -> CheckResult:
        """
        Verify project structure matches expected layout.

        Returns:
            CheckResult indicating whether all required files and directories exist
        """
        try:
            missing = []
            for fn in PROJECT_STRUCTURE["files"]:
                if not (self.project_root / fn).exists():
                    missing.append(fn)
            for dn in PROJECT_STRUCTURE["dirs"]:
                if not (self.project_root / dn).is_dir():
                    missing.append(dn + "/")
            if missing:
                return CheckResult(
                    name="Project structure",
                    status=False,
                    details=f"Missing: {', '.join(missing)}",
                    recommendations=["Ensure all core files and directories exist"],
                )
            return CheckResult(
                name="Project structure",
                status=True,
                details="All files & dirs present",
            )
        except Exception as e:
            logger.error(f"Error checking project structure: {e}")
            return CheckResult(
                name="Project structure",
                status=False,
                details=f"Error: {str(e)}",
                recommendations=["Check file system permissions"],
            )

    def check_pytest(self) -> CheckResult:
        """
        Run pytest to verify test coverage and functionality.

        Returns:
            CheckResult indicating whether all tests pass
        """
        try:
            res = subprocess.run(
                ["pytest", "tests", "-q", "--maxfail=1", "--disable-warnings"],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                return CheckResult(
                    name="Pytest",
                    status=False,
                    details=res.stdout + res.stderr,
                    recommendations=["Fix failing tests"],
                )
            return CheckResult(name="Pytest", status=True, details="All tests passed")
        except Exception as e:
            logger.error(f"Error running pytest: {e}")
            return CheckResult(
                name="Pytest",
                status=False,
                details=str(e),
                recommendations=[
                    "Ensure pytest is installed and tests directory is valid"
                ],
            )

    def check_flake8(self) -> CheckResult:
        """
        Run flake8 to verify code style and quality.

        Returns:
            CheckResult indicating whether code meets style requirements
        """
        try:
            res = subprocess.run(["flake8", "."], capture_output=True, text=True)
            if res.returncode != 0:
                return CheckResult(
                    name="Flake8",
                    status=False,
                    details=res.stdout,
                    recommendations=["Run flake8 and fix style violations"],
                )
            return CheckResult(name="Flake8", status=True, details="No style issues")
        except Exception as e:
            logger.error(f"Error running flake8: {e}")
            return CheckResult(
                name="Flake8",
                status=False,
                details=str(e),
                recommendations=["Install flake8 or fix configuration"],
            )

    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        for root, _, files in os.walk(self.project_root):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)
        return python_files

    def _check_required_files(self) -> Set[str]:
        """Check for required files and directories."""
        missing_files = set()
        for file in self.required_files:
            path = self.project_root / file
            if not path.exists():
                missing_files.add(file)
        return missing_files

    def _check_docstring(self, tree: ast.AST) -> bool:
        """Check if the module/class/function has docstrings."""
        has_docstring = False

        # Check module docstring
        if (
            isinstance(tree, ast.Module)
            and tree.body
            and isinstance(tree.body[0], ast.Expr)
        ):
            if isinstance(tree.body[0].value, ast.Str):
                has_docstring = True

        # Check class and function docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Str)
                ):
                    has_docstring = True
                else:
                    has_docstring = False
                    break

        return has_docstring

    def _check_type_hints(self, content: str) -> bool:
        """Check if the code has type hints."""
        try:
            tree = ast.parse(content)
            has_hints = False

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check return type annotation
                    if node.returns:
                        has_hints = True
                    # Check argument type annotations
                    for arg in node.args.args:
                        if arg.annotation:
                            has_hints = True
                            break
                    if has_hints:
                        break

            return has_hints
        except SyntaxError:
            return False

    def _check_error_handling(self, tree: ast.AST) -> bool:
        """Check if the code has proper error handling."""
        has_error_handling = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                has_error_handling = True
                break

        return has_error_handling

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate the cyclomatic complexity of the code."""
        complexity = 1  # Base complexity
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler)
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.FunctionDef):
                complexity += 1
        return complexity

    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            # Only analyze if there is at least one function or class definition
            has_code = any(
                isinstance(node, (ast.FunctionDef, ast.ClassDef))
                for node in ast.walk(tree)
            )
            if not has_code:
                return
            analysis = FileAnalysis()

            # Check docstrings
            analysis.has_docstring = self._check_docstring(tree)
            if not analysis.has_docstring:
                analysis.issues.append("Missing module/class/function docstrings")

            # Check type hints
            analysis.has_type_hints = self._check_type_hints(content)
            if not analysis.has_type_hints:
                analysis.issues.append("Missing type hints")

            # Check error handling
            analysis.has_error_handling = self._check_error_handling(tree)
            if not analysis.has_error_handling:
                analysis.issues.append("Missing error handling")

            # Calculate complexity
            analysis.complexity = self._calculate_complexity(tree)
            if analysis.complexity > 10:
                analysis.issues.append(f"High complexity: {analysis.complexity}")

            # Set test coverage (placeholder)
            analysis.test_coverage = 0.5

            self.analysis_results[
                str(file_path.relative_to(self.project_root))
            ] = analysis

        except SyntaxError as e:
            logging.error(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logging.error(f"Error analyzing {file_path}: {e}")

    def _calculate_scores(self) -> Dict[str, float]:
        """Calculate overall scores based on analysis results."""
        if not self.analysis_results or len(self.analysis_results) == 0:
            return {
                "documentation": 0.0,
                "type_safety": 0.0,
                "error_handling": 0.0,
                "complexity": 0.0,
                "test_coverage": 0.0,
                "overall": 0.0,
            }

        total_files = len(self.analysis_results)
        scores = {
            "documentation": sum(
                1 for a in self.analysis_results.values() if a.has_docstring
            )
            / total_files,
            "type_safety": sum(
                1 for a in self.analysis_results.values() if a.has_type_hints
            )
            / total_files,
            "error_handling": sum(
                1 for a in self.analysis_results.values() if a.has_error_handling
            )
            / total_files,
            "complexity": sum(
                1 for a in self.analysis_results.values() if a.complexity <= 10
            )
            / total_files,
            "test_coverage": sum(
                a.test_coverage for a in self.analysis_results.values()
            )
            / total_files,
        }

        # Calculate overall score (weighted average)
        weights = {
            "documentation": 0.2,
            "type_safety": 0.2,
            "error_handling": 0.2,
            "complexity": 0.2,
            "test_coverage": 0.2,
        }

        scores["overall"] = sum(scores[k] * weights[k] for k in weights)
        return scores

    def analyze_project(self) -> Dict[str, Any]:
        """Analyze the entire project and generate a report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "missing_files": list(self._check_required_files()),
            "file_analysis": {},
            "scores": {},
            "beta_ready": False,
        }

        # Analyze Python files
        python_files = self._find_python_files()
        non_empty_files = []
        self.analysis_results = {}
        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    non_empty_files.append(file_path)
                    self._analyze_file(file_path)

        # Add analysis results to report
        report["file_analysis"] = {
            path: {
                "has_docstring": analysis.has_docstring,
                "has_type_hints": analysis.has_type_hints,
                "has_error_handling": analysis.has_error_handling,
                "complexity": analysis.complexity,
                "test_coverage": analysis.test_coverage,
                "issues": analysis.issues,
            }
            for path, analysis in self.analysis_results.items()
        }

        # Calculate scores
        if not non_empty_files:
            report["scores"] = {
                "documentation": 0.0,
                "type_safety": 0.0,
                "error_handling": 0.0,
                "complexity": 0.0,
                "test_coverage": 0.0,
                "overall": 0.0,
            }
        else:
            report["scores"] = self._calculate_scores()

        # Determine if project is beta ready
        report["beta_ready"] = (
            len(report["missing_files"]) == 0
            and report["scores"]["overall"] >= 0.8
            and all(
                analysis.has_docstring for analysis in self.analysis_results.values()
            )
            and all(
                analysis.has_error_handling
                for analysis in self.analysis_results.values()
            )
        )

        return report

    def run_all(self) -> List[CheckResult]:
        """
        Run all verification checks.

        Returns:
            List of CheckResults for all performed checks
        """
        try:
            self.results = [
                self.check_env_files(),
                self.check_env_vars(),
                self.check_requirements(),
                self.check_structure(),
                self.check_pytest(),
                self.check_flake8(),
            ]
            return self.results
        except Exception as e:
            logger.error(f"Error running verification checks: {e}")
            raise

    def generate_markdown(self) -> str:
        """
        Generate a human-readable Markdown report.

        Returns:
            Markdown formatted report string
        """
        try:
            now = datetime.now().isoformat()
            lines = [
                f"# AutoBlogger Beta Verification",
                f"- Generated: {now}",
                f"- Passed: {sum(r.status for r in self.results)}/{len(self.results)}",
                "",
            ]
            for r in self.results:
                status = "✅" if r.status else "❌"
                lines.append(f"## {status} {r.name}")
                lines.append(f"- {r.details}")
                if r.recommendations:
                    lines.append("- Recommendations:")
                    for rec in r.recommendations:
                        lines.append(f"  - {rec}")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error generating markdown report: {e}")
            raise


def main() -> None:
    """Main entry point for the verification script."""
    try:
        parser = argparse.ArgumentParser(
            description="Verify AutoBlogger beta readiness"
        )
        parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
        parser.add_argument("--output", "-o", help="Write Markdown report to file")
        args = parser.parse_args()

        verifier = AutoBloggerVerifier(os.getcwd())
        results = verifier.run_all()

        if args.json:
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            report = verifier.generate_markdown()
            if args.output:
                Path(args.output).write_text(report, encoding="utf-8")
            print(report)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    main()
