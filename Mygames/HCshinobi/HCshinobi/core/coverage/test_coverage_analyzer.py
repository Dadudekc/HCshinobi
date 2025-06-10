"""Test coverage analyzer for HCshinobi commands."""
import os
import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import json
from datetime import datetime
import ast
from collections import defaultdict

logger = logging.getLogger(__name__)

class CodeComplexityAnalyzer:
    """Analyzes code complexity metrics."""
    
    def __init__(self):
        """Initialize the complexity analyzer."""
        self.visitor = ComplexityVisitor()
        
    def analyze_complexity(self, code: str) -> Dict:
        """Analyze code complexity metrics."""
        try:
            tree = ast.parse(code)
            self.visitor.visit(tree)
            return {
                "cyclomatic_complexity": self.visitor.cyclomatic_complexity,
                "max_nesting": self.visitor.max_nesting,
                "branch_count": self.visitor.branch_count,
                "function_count": self.visitor.function_count
            }
        except Exception as e:
            logger.error(f"Error analyzing complexity: {e}")
            return {
                "cyclomatic_complexity": 0,
                "max_nesting": 0,
                "branch_count": 0,
                "function_count": 0
            }

class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor for complexity analysis."""
    
    def __init__(self):
        """Initialize the visitor."""
        self.cyclomatic_complexity = 1
        self.max_nesting = 0
        self.branch_count = 0
        self.function_count = 0
        self.current_nesting = 0
        
    def visit_FunctionDef(self, node):
        """Visit function definition."""
        self.function_count += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1
        
    def visit_If(self, node):
        """Visit if statement."""
        self.cyclomatic_complexity += 1
        self.branch_count += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1
        
    def visit_For(self, node):
        """Visit for loop."""
        self.cyclomatic_complexity += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1
        
    def visit_While(self, node):
        """Visit while loop."""
        self.cyclomatic_complexity += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1
        
    def visit_Try(self, node):
        """Visit try block."""
        self.cyclomatic_complexity += 1
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1

class TestCoverageAnalyzer:
    """Analyzes test coverage for commands and generates test stubs."""
    
    def __init__(self, bot_root: str = "HCshinobi"):
        """Initialize the analyzer."""
        self.bot_root = Path(bot_root)
        self.test_dir = self.bot_root / "tests"
        self.cogs_dir = self.bot_root / "bot" / "cogs"
        
        # Load command metrics for prioritization
        self.metrics_file = self.bot_root / "data" / "metrics" / "command_metrics.json"
        self.command_metrics = self._load_command_metrics()
        
        # Load feedback data
        self.feedback_file = self.bot_root / "data" / "feedback_memory.json"
        self.feedback_data = self._load_feedback_data()
        
        # Initialize complexity analyzer
        self.complexity_analyzer = CodeComplexityAnalyzer()
        
        # Game-specific patterns
        self.game_patterns = {
            "state_validation": re.compile(r"game_state|player_state|validate_state"),
            "player_data": re.compile(r"player_data|inventory|stats|level"),
            "game_balance": re.compile(r"balance|difficulty|scaling|reward"),
            "resource_management": re.compile(r"resource|energy|health|mana")
        }
        
        # TODO categories and weights
        self.todo_weights = {
            "SECURITY_CONCERN": 1.0,
            "MISSING_IMPLEMENTATION": 0.8,
            "IMPORTANT": 0.7,
            "ENHANCEMENT": 0.5,
            "INCOMPLETE": 0.6,
            "YOU_MAY_WANT_TO_CHECK": 0.4,
            "PLACEHOLDER": 0.3,
            "GENERAL": 0.2
        }
        
    def _load_command_metrics(self) -> Dict:
        """Load command metrics for prioritization."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Failed to load command metrics")
        return {}
        
    def _load_feedback_data(self) -> Dict:
        """Load feedback data for error analysis."""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("Failed to load feedback data")
        return {}
        
    def _get_command_usage_rank(self, command_name: str) -> int:
        """Get the usage rank of a command (lower is more used)."""
        if not self.command_metrics:
            return 999  # Default to low priority if no metrics
            
        # Sort commands by total uses
        sorted_commands = sorted(
            self.command_metrics.items(),
            key=lambda x: x[1]["total_uses"],
            reverse=True
        )
        
        # Find the command's rank
        for rank, (name, _) in enumerate(sorted_commands, 1):
            if name == command_name:
                return rank
        return 999
        
    def _find_command_tests(self) -> Dict[str, Set[str]]:
        """Find all test files and their covered commands."""
        test_files = {}
        
        # Walk through test directory
        for root, _, files in os.walk(self.test_dir):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    file_path = Path(root) / file
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                    # Find test classes and methods
                    test_classes = re.findall(r"class Test(\w+)\(.*\):", content)
                    test_methods = re.findall(r"async def test_(\w+)\(.*\):", content)
                    
                    # Map test methods to commands
                    covered_commands = set()
                    for method in test_methods:
                        # Try to match test method to command name
                        for cmd in self.command_metrics.keys():
                            if cmd.lower() in method.lower():
                                covered_commands.add(cmd)
                                
                    test_files[str(file_path)] = covered_commands
                    
        return test_files
        
    def _analyze_complexity(self, code: str) -> Dict:
        """Analyze code complexity metrics."""
        try:
            tree = ast.parse(code)
            analyzer = CodeComplexityAnalyzer()
            analyzer.visit(tree)
            
            return {
                "cyclomatic_complexity": analyzer.visitor.cyclomatic_complexity,
                "max_nesting": analyzer.visitor.max_nesting,
                "branch_count": analyzer.visitor.branch_count,
                "function_count": analyzer.visitor.function_count
            }
        except Exception as e:
            logger.error(f"Failed to analyze code complexity: {e}")
            return {
                "cyclomatic_complexity": 0,
                "max_nesting": 0,
                "branch_count": 0,
                "function_count": 0
            }
            
    def _get_command_complexity(self, command_name: str) -> Dict:
        """Get complexity metrics for a command."""
        # Find command file
        for root, _, files in os.walk(self.cogs_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                    # Find command function
                    pattern = rf"@app_commands\.command\(.*name=['\"]{command_name}['\"].*\)\s+async def {command_name}\("
                    if re.search(pattern, content):
                        # Extract function body
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.AsyncFunctionDef) and node.name == command_name:
                                # Get function source
                                start_line = node.lineno
                                end_line = node.end_lineno
                                function_code = "\n".join(content.split("\n")[start_line-1:end_line])
                                return self._analyze_complexity(function_code)
                                
        return {
            "cyclomatic_complexity": 0,
            "max_nesting": 0,
            "branch_count": 0,
            "function_count": 0
        }
        
    def _get_command_error_rate(self, command_name: str) -> float:
        """Get error rate for a command from feedback data."""
        if not self.feedback_data:
            return 0.0
            
        command_feedback = self.feedback_data.get(command_name, {})
        total_uses = command_feedback.get("total_uses", 0)
        error_count = command_feedback.get("error_count", 0)
        
        return error_count / total_uses if total_uses > 0 else 0.0
        
    def _load_todo_report(self) -> Dict:
        """Load TODO report from JSON file."""
        try:
            report_file = self.bot_root / "todo_report_categories" / "todo_report.json"
            if report_file.exists():
                with open(report_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading TODO report: {e}")
        return {}
        
    def _analyze_todo_impact(self, file_path: Path) -> float:
        """Analyze TODO impact for a file."""
        todo_report = self._load_todo_report()
        impact_score = 0.0
        
        # Get TODOs for this file
        file_todos = todo_report.get(str(file_path), {})
        
        # Calculate weighted impact
        for category, count in file_todos.items():
            weight = self.todo_weights.get(category, 0.1)
            impact_score += count * weight
            
        return impact_score
        
    def _find_untested_commands(self) -> List[Dict]:
        """Find commands that need test coverage."""
        test_files = self._find_command_tests()
        all_commands = set(self.command_metrics.keys())
        covered_commands = set()
        
        # Get all covered commands
        for covered in test_files.values():
            covered_commands.update(covered)
            
        # Find untested commands
        untested = all_commands - covered_commands
        
        # Create prioritized list of untested commands
        untested_with_priority = []
        for cmd in untested:
            # Get complexity metrics
            complexity = self._get_command_complexity(cmd)
            error_rate = self._get_command_error_rate(cmd)
            
            # Analyze TODO impact
            todo_impact = self._analyze_todo_impact(Path(cmd))
            
            # Calculate priority score
            # Higher complexity and error rate = higher priority
            priority_score = (
                complexity["cyclomatic_complexity"] * 0.4 +
                complexity["max_nesting"] * 0.3 +
                error_rate * 100 * 0.3 +
                todo_impact * 0.2
            )
            
            untested_with_priority.append({
                "command": cmd,
                "usage_rank": self._get_command_usage_rank(cmd),
                "total_uses": self.command_metrics.get(cmd, {}).get("total_uses", 0),
                "success_rate": self.command_metrics.get(cmd, {}).get("successful_uses", 0) / 
                              self.command_metrics.get(cmd, {}).get("total_uses", 1) if 
                              self.command_metrics.get(cmd, {}).get("total_uses", 0) > 0 else 0,
                "complexity": complexity,
                "error_rate": error_rate,
                "todo_impact": todo_impact,
                "priority_score": priority_score
            })
            
        # Sort by priority score (higher score = higher priority)
        return sorted(untested_with_priority, key=lambda x: x["priority_score"], reverse=True)
        
    def _analyze_security_concerns(self, code: str) -> List[str]:
        """Analyze code for game-specific concerns."""
        concerns = []
        for concern_type, pattern in self.game_patterns.items():
            if pattern.search(code):
                concerns.append(concern_type)
        return concerns
        
    def _generate_security_test_cases(self, command_name: str, code: str) -> List[str]:
        """Generate game-focused test cases."""
        concerns = self._analyze_security_concerns(code)
        test_cases = []
        
        if "state_validation" in concerns:
            test_cases.extend([
                "# Test game state validation",
                "# Test state transitions",
                "# Test state persistence"
            ])
            
        if "player_data" in concerns:
            test_cases.extend([
                "# Test player data integrity",
                "# Test inventory management",
                "# Test stat calculations"
            ])
            
        if "game_balance" in concerns:
            test_cases.extend([
                "# Test difficulty scaling",
                "# Test reward calculations",
                "# Test progression balance"
            ])
            
        if "resource_management" in concerns:
            test_cases.extend([
                "# Test resource consumption",
                "# Test resource regeneration",
                "# Test resource limits"
            ])
            
        return test_cases
        
    def _generate_test_stub(self, command_info: Dict) -> str:
        """Generate a test stub for a command."""
        complexity = command_info["complexity"]
        usage_stats = command_info["usage_stats"]
        todo_impact = command_info["todo_impact"]
        
        # Read command file content
        with open(command_info["file"], 'r') as f:
            code = f.read()
            
        # Generate test cases based on complexity and security
        test_cases = []
        
        # Add complexity-based test cases
        if complexity["cyclomatic_complexity"] > 5:
            test_cases.append("# Test complex branching paths")
        if complexity["max_nesting"] > 2:
            test_cases.append("# Test nested condition handling")
        if usage_stats["error_rate"] > 0.1:
            test_cases.append("# Test error handling scenarios")
            
        # Add security-focused test cases
        security_cases = self._generate_security_test_cases(
            command_info["command"],
            code
        )
        test_cases.extend(security_cases)
        
        # Add TODO-related test cases
        if todo_impact > 0.5:
            test_cases.append("# Test TODO-related edge cases")
            
        test_cases_str = "\n    ".join(test_cases) if test_cases else "# Add test cases here"
        
        return f'''"""Test stub for {command_info['command']} command.

Complexity Metrics:
- Cyclomatic Complexity: {complexity['cyclomatic_complexity']}
- Max Nesting: {complexity['max_nesting']}
- Branch Count: {complexity['branch_count']}
- Function Count: {complexity['function_count']}

Usage Stats:
- Total Uses: {usage_stats['total_uses']}
- Success Rate: {1 - usage_stats['error_rate']:.1%}
- Error Rate: {usage_stats['error_rate']:.1%}

TODO Impact: {todo_impact:.2f}
Security Concerns: {', '.join(self._analyze_security_concerns(code))}
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from discord.ext import commands
from discord import app_commands

@pytest.fixture
def cog():
    """Create a cog instance."""
    # Import and instantiate the cog
    return None  # Replace with actual cog import

@pytest.fixture
def interaction():
    """Create a mock interaction."""
    mock = AsyncMock()
    mock.response = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_{command_info['command']}(cog, interaction):
    """Test the {command_info['command']} command."""
    {test_cases_str}
    
    # Implement test cases here
    pass
'''
        return stub
        
    def analyze_coverage(self) -> Dict:
        """Analyze test coverage and generate test stubs."""
        untested_commands = self._find_untested_commands()
        
        # Generate test stubs
        test_stubs = {}
        for cmd in untested_commands:
            test_stubs[cmd["command"]] = {
                "stub": self._generate_test_stub(cmd),
                "priority": cmd["priority_score"],
                "usage_stats": {
                    "total_uses": cmd["total_uses"],
                    "success_rate": cmd["success_rate"],
                    "error_rate": cmd["error_rate"]
                },
                "complexity": cmd["complexity"]
            }
            
        # Create task queue
        task_queue = []
        for cmd_name, stub_data in test_stubs.items():
            task_queue.append({
                "type": "test_generation",
                "command": cmd_name,
                "priority": stub_data["priority"],
                "target_file": f"tests/test_commands/test_{cmd_name}.py",
                "stub": stub_data["stub"],
                "usage_stats": stub_data["usage_stats"],
                "complexity": stub_data["complexity"],
                "created_at": datetime.utcnow().isoformat()
            })
            
        return {
            "untested_commands": len(untested_commands),
            "total_commands": len(self.command_metrics),
            "coverage_percentage": (len(self.command_metrics) - len(untested_commands)) / len(self.command_metrics) * 100 if self.command_metrics else 0,
            "task_queue": sorted(task_queue, key=lambda x: x["priority"], reverse=True),
            "test_stubs": test_stubs
        }
        
    def save_task_queue(self, task_queue: List[Dict], output_file: str = "data/tasks/test_generation_queue.json"):
        """Save the task queue to a file."""
        output_path = self.bot_root / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w') as f:
                json.dump(task_queue, f, indent=2)
            logger.info(f"Saved test generation task queue to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save task queue: {e}")
            
    def generate_test_files(self, output_dir: str = "tests/test_commands"):
        """Generate test stub files."""
        output_path = self.bot_root / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        analysis = self.analyze_coverage()
        
        for cmd_name, stub_data in analysis["test_stubs"].items():
            file_path = output_path / f"test_{cmd_name}.py"
            try:
                with open(file_path, 'w') as f:
                    f.write(stub_data["stub"])
                logger.info(f"Generated test stub for {cmd_name}")
            except Exception as e:
                logger.error(f"Failed to generate test stub for {cmd_name}: {e}")
                
        # Save task queue
        self.save_task_queue(analysis["task_queue"])
        
        return analysis 