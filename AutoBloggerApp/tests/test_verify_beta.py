"""
Tests for the beta verification functionality.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from autoblogger.verify_beta import AutoBloggerVerifier, CheckResult
import ast


@pytest.fixture
def project_root(tmp_path):
    """Create a temporary project structure."""
    # Create project structure
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    # Create some Python files
    (tmp_path / "src" / "__init__.py").touch()
    (tmp_path / "src" / "main.py").write_text(
        '''
"""
Main module docstring.
"""
from typing import List, Dict

def main() -> None:
    """Main function docstring."""
    try:
        print("Hello, World!")
    except Exception as e:
        print(f"Error: {e}")
'''
    )

    # Create a file without docstring
    (tmp_path / "src" / "no_docstring.py").write_text(
        """
def bad_function():
    print("No docstring here")
"""
    )

    return tmp_path


@pytest.fixture
def verifier(project_root):
    """Create a BetaVerifier instance."""
    return AutoBloggerVerifier(str(project_root))


def test_verifier_initialization(project_root):
    """Test BetaVerifier initialization."""
    verifier = AutoBloggerVerifier(str(project_root))

    assert verifier.project_root == Path(project_root)
    assert verifier.analysis_results == {}
    assert "README.md" in verifier.required_files
    assert "requirements.txt" in verifier.required_files


def test_check_required_files(verifier, project_root):
    """Test checking for required files."""
    missing_files = verifier._check_required_files()

    assert "README.md" in missing_files
    assert "requirements.txt" in missing_files
    assert "setup.py" in missing_files


def test_find_python_files(verifier, project_root):
    """Test finding Python files."""
    python_files = verifier._find_python_files()

    assert len(python_files) == 3  # main.py, no_docstring.py, __init__.py
    assert any("main.py" in str(f) for f in python_files)
    assert any("no_docstring.py" in str(f) for f in python_files)


def test_analyze_file_with_docstring(verifier, project_root):
    """Test analyzing a file with proper docstring."""
    file_path = project_root / "src" / "main.py"
    verifier._analyze_file(file_path)

    analysis = verifier.analysis_results[str(file_path.relative_to(project_root))]
    assert analysis.has_docstring
    assert analysis.has_type_hints
    assert analysis.has_error_handling
    assert analysis.complexity > 0
    assert analysis.test_coverage == 0.5  # Default value


def test_analyze_file_without_docstring(verifier, project_root):
    """Test analyzing a file without docstring."""
    file_path = project_root / "src" / "no_docstring.py"
    verifier._analyze_file(file_path)

    analysis = verifier.analysis_results[str(file_path.relative_to(project_root))]
    assert not analysis.has_docstring
    assert not analysis.has_type_hints
    assert not analysis.has_error_handling
    assert "Missing module/class/function docstrings" in analysis.issues


def test_check_docstring(verifier):
    """Test docstring checking."""
    # Test with docstring
    tree_with_docstring = verifier._check_docstring(
        ast.parse(
            '''
"""
Module docstring.
"""
def function():
    """Function docstring."""
    pass
'''
        )
    )
    assert tree_with_docstring

    # Test without docstring
    tree_without_docstring = verifier._check_docstring(
        ast.parse(
            """
def function():
    pass
"""
        )
    )
    assert not tree_without_docstring


def test_check_type_hints(verifier):
    """Test type hints checking."""
    # Test with type hints
    content_with_hints = """
from typing import List, Dict

def function(x: int) -> str:
    return str(x)
"""
    assert verifier._check_type_hints(content_with_hints)

    # Test without type hints
    content_without_hints = """
def function(x):
    return str(x)
"""
    assert not verifier._check_type_hints(content_without_hints)


def test_check_error_handling(verifier):
    """Test error handling checking."""
    # Test with error handling
    tree_with_handling = ast.parse(
        """
try:
    x = 1
except Exception as e:
    print(e)
"""
    )
    assert verifier._check_error_handling(tree_with_handling)

    # Test without error handling
    tree_without_handling = ast.parse(
        """
x = 1
print(x)
"""
    )
    assert not verifier._check_error_handling(tree_without_handling)


def test_calculate_complexity(verifier):
    """Test complexity calculation."""
    # Test with complex code
    complex_tree = ast.parse(
        """
def complex_function():
    if True:
        for i in range(10):
            while i > 0:
                try:
                    x = 1
                except:
                    pass
"""
    )
    assert verifier._calculate_complexity(complex_tree) > 5

    # Test with simple code
    simple_tree = ast.parse(
        """
def simple_function():
    x = 1
    return x
"""
    )
    assert verifier._calculate_complexity(simple_tree) == 2


def test_calculate_scores(verifier, project_root):
    """Test score calculation."""
    # Analyze some files
    verifier._analyze_file(project_root / "src" / "main.py")
    verifier._analyze_file(project_root / "src" / "no_docstring.py")

    scores = verifier._calculate_scores()

    assert "documentation" in scores
    assert "type_safety" in scores
    assert "error_handling" in scores
    assert "complexity" in scores
    assert "test_coverage" in scores
    assert "overall" in scores
    assert 0 <= scores["overall"] <= 1


def test_analyze_project(verifier, project_root):
    """Test full project analysis."""
    report = verifier.analyze_project()

    assert "timestamp" in report
    assert "missing_files" in report
    assert "file_analysis" in report
    assert "scores" in report
    assert "beta_ready" in report
    assert isinstance(report["beta_ready"], bool)


def test_analyze_project_empty(verifier, tmp_path):
    """Test analyzing an empty project."""
    # Clean up any Python files in the test directory
    for py_file in tmp_path.rglob("*.py"):
        py_file.unlink()

    verifier = AutoBloggerVerifier(str(tmp_path))
    report = verifier.analyze_project()

    assert report["scores"]["overall"] == 0.0
    assert len(report["file_analysis"]) == 0
    assert not report["beta_ready"]


def test_analyze_project_with_errors(verifier, project_root):
    """Test analyzing a project with errors."""
    # Create a file with syntax error
    bad_file = project_root / "src" / "syntax_error.py"
    bad_file.write_text("def bad_function()\n    pass")  # Missing colon

    report = verifier.analyze_project()

    assert "syntax_error.py" not in report["file_analysis"]
    assert report["scores"]["overall"] < 1.0
