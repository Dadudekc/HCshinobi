#!/usr/bin/env python3
"""
generate_missing_tests.py

Identifies modules and files without corresponding test files and generates them.
This helps ensure comprehensive test coverage across the codebase.

Usage:
    python generate_missing_tests.py [--auto-generate] [--module=<module_name>]
        [--run-tests] [--use-ollama] [--summary-only]
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
import importlib.util
import inspect

# Configuration
PROJECT_ROOT = Path(".").resolve()
TEST_DIR = PROJECT_ROOT / "tests"
CACHE_PATH = PROJECT_ROOT / ".test_gen_cache.json"

def find_module_dirs(root=PROJECT_ROOT):
    """Find all Python packages (directories with __init__.py) excluding tests."""
    return [
        str(p.parent.relative_to(root))
        for p in root.glob("**/__init__.py")
        if "tests" not in str(p)
    ]

MODULE_DIRS = find_module_dirs()

def module_to_test_filename(module_path: Path) -> str:
    """Map a module filename to its corresponding test filename."""
    return f"test_{module_path.stem}.py"

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate tests for files without tests')
    parser.add_argument('--auto-generate', action='store_true',
                        help='Automatically generate test files for modules without tests')
    parser.add_argument('--module', type=str, help='Generate tests for a specific module only')
    parser.add_argument('--min-methods', type=int, default=1,
                        help='Minimum number of methods to consider a file for testing')
    parser.add_argument('--run-tests', action='store_true',
                        help='Run pytest on the generated tests')
    parser.add_argument('--use-ollama', action='store_true',
                        help='Use Ollama for test generation instead of templates')
    parser.add_argument('--summary-only', action='store_true',
                        help='Print summary of modules without tests but do not generate files')
    return parser.parse_args()

def load_cache():
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def save_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, indent=4), encoding='utf-8')

def find_python_modules():
    """Find all Python modules in the codebase."""
    modules = []
    for module_dir in MODULE_DIRS:
        module_path = PROJECT_ROOT / module_dir
        if not module_path.exists():
            continue
        for root, _, filenames in os.walk(module_path):
            for filename in filenames:
                if filename.endswith('.py') and not filename.startswith('__'):
                    file_path = Path(root) / filename
                    rel_path = file_path.relative_to(PROJECT_ROOT)
                    module_name = str(rel_path).replace(os.sep, ".")[:-3]
                    modules.append({
                        'path': file_path,
                        'relative_path': rel_path,
                        'name': module_name
                    })
    return modules

def find_existing_tests():
    """Find all existing test files."""
    tests = {}
    if not TEST_DIR.exists():
        return tests
    for root, _, filenames in os.walk(TEST_DIR):
        for filename in filenames:
            if filename.startswith('test_') and filename.endswith('.py'):
                test_path = Path(root) / filename
                tests[filename] = test_path
    return tests

def analyze_module_content(module_path):
    """Analyze module content to determine if it needs tests."""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        spec = importlib.util.spec_from_file_location("module.name", module_path)
        if spec is None or spec.loader is None:
            return {'classes': [], 'functions': [], 'needs_test': False}
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            classes = []
            functions = []
            for name, obj in inspect.getmembers(module):
                if name.startswith('_'):
                    continue
                if inspect.isclass(obj) and obj.__module__ == module.__name__:
                    methods = [m for m, _ in inspect.getmembers(obj, inspect.isfunction) if not m.startswith('_')]
                    if methods:
                        classes.append({'name': name, 'methods': methods})
                elif inspect.isfunction(obj) and obj.__module__ == module.__name__:
                    # Try to get parameter names for better test case generation
                    param_names = []
                    try:
                        sig = inspect.signature(obj)
                        param_names = [p for p in sig.parameters.keys() if p != 'self']
                    except (ValueError, TypeError):
                        pass
                    functions.append({'name': name, 'parameters': param_names})
            needs_test = bool(classes or functions)
            return {
                'classes': classes,
                'functions': functions,
                'needs_test': needs_test
            }
        except Exception as e:
            has_class = 'class ' in content
            has_function = 'def ' in content and not content.strip().startswith('def test_')
            return {
                'classes': [{'name': 'Unknown', 'methods': []}] if has_class else [],
                'functions': ['unknown_function'] if has_function else [],
                'needs_test': has_class or has_function,
                'import_error': str(e)
            }
    except Exception as e:
        return {
            'error': str(e),
            'needs_test': False
        }

def generate_test_template(module_info):
    """
    Generate a test file template for a module using unittest and pytest.
    
    This function builds a test class named based on the module's last part.
    It creates placeholder test methods for each public class method and function.
    """
    module_path = module_info['path']
    module_name = module_info['name']
    # Read module source if needed (currently unused)
    with open(module_path, 'r', encoding='utf-8') as f:
        module_content = f.read()

    # Generate import statement based on module name.
    if module_name.startswith('chat_mate.'):
        import_stmt = f"from {module_name} import *"
        # Extract the class name for better imports
        module_simple_name = module_name.split('.')[-1]
    else:
        import_stmt = f"import {module_name}"
        module_simple_name = module_name.split('.')[-1]

    test_class_name = f"Test{module_simple_name.capitalize()}"

    test_content = f"""import unittest
import pytest
from unittest.mock import Mock, patch, MagicMock
{import_stmt}

class {test_class_name}(unittest.TestCase):
    \"\"\"Tests for {module_name} module.\"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures, if any.\"\"\"
        # Initialize common test fixtures
        self.valid_inputs = {{"string": "test", "int": 42, "list": [1, 2, 3], "dict": {{"key": "value"}}}}
        self.invalid_inputs = {{"none": None, "empty_string": "", "zero": 0, "empty_list": []}}
"""

    # Check if we need tearDown method based on certain patterns in the code
    needs_teardown = any(pattern in module_content for pattern in 
                         ['open(', 'connect(', 'create_engine(', 'tempfile', 'setUp'])
    
    if needs_teardown:
        test_content += """
    def tearDown(self):
        \"\"\"Tear down test fixtures, if any.\"\"\"
        # Clean up resources
        for attr in dir(self):
            if attr.startswith('mock_'):
                patcher = getattr(self, attr)
                if hasattr(patcher, 'stop') and callable(patcher.stop):
                    patcher.stop()
"""
    else:
        test_content += """
    def tearDown(self):
        \"\"\"Tear down test fixtures, if any.\"\"\"
        pass
"""

    # Add test methods for each class in the module.
    for cls in module_info['content'].get('classes', []):
        cls_name = cls['name']
        
        # Add class setup if we have classes
        test_content += f"""
    def _create_test_{cls_name.lower()}(self):
        \"\"\"Helper to create a test instance of {cls_name} with appropriate mocks.\"\"\"
        # Create an instance with appropriate test parameters
        try:
            return {cls_name}()  # Add required parameters based on class requirements
        except TypeError as e:
            # If the constructor requires parameters, try to create with mocks
            # This is just a template - adjust parameters as needed for your class
            self.skipTest(f"Cannot create {cls_name} instance without parameters: {{e}}")
"""
        
        for method in cls['methods']:
            # Check method name patterns
            if method.startswith(('get_', 'fetch_', 'retrieve_', 'find_', 'load_')):
                # Retrieval methods
                test_content += _generate_retrieval_test(cls_name, method)
            elif method.startswith(('set_', 'update_', 'modify_', 'change_')):
                # Setter methods
                test_content += _generate_setter_test(cls_name, method)
            elif method.startswith(('create_', 'add_', 'insert_', 'new_')):
                # Creation methods
                test_content += _generate_creation_test(cls_name, method)
            elif method.startswith(('delete_', 'remove_', 'clear_')):
                # Deletion methods
                test_content += _generate_deletion_test(cls_name, method)
            elif method.startswith(('is_', 'has_', 'can_', 'should_', 'check_', 'validate_')):
                # Boolean validation methods
                test_content += _generate_validation_test(cls_name, method)
            elif method.startswith(('process_', 'handle_', 'execute_', 'run_', 'perform_')):
                # Processing methods
                test_content += _generate_processing_test(cls_name, method)
            else:
                # General method test
                test_content += f"""
    def test_{method}_should_work(self):
        \"\"\"Test that {cls_name}.{method} works as expected.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Mock dependencies as needed
        expected_result = "expected result"  # Update with appropriate expected value
        
        # Act
        try:
            # Try to get method signature to determine parameters
            result = instance.{method}()  # Add parameters if needed
            
            # Assert
            self.assertIsNotNone(result, "Method should return a value")
            # Add more specific assertions based on expected behavior
        except Exception as e:
            # This is just scaffolding - add proper parameters and assertions
            # based on the actual method signature and behavior
            self.fail(f"Method raised an exception: {{e}}")
"""

    # Add parametrized test methods for each function in the module.
    for func_item in module_info['content'].get('functions', []):
        if isinstance(func_item, dict):
            func = func_item["name"]
            param_names = func_item.get("parameters", [])
        else:
            func = func_item
            param_names = []
        
        # Check function name patterns
        if func.startswith(('get_', 'fetch_', 'retrieve_', 'find_', 'load_')):
            # Data retrieval function
            test_content += f"""
    @pytest.mark.parametrize("input_value,expected", [
        ("valid_id", {{"expected": "data"}}),  # Happy path
        ("", None),  # Empty input
        (None, None),  # None input
        # Add more test cases as needed
    ])
    def test_{func}_retrieves_data(self, input_value, expected):
        \"\"\"Test {func} retrieves the expected data.\"\"\"
        # Arrange - set up any mocks or fixtures
        
        # Act
        result = {func}(input_value)
        
        # Assert
        assert result == expected, f"Expected {{expected}} but got {{result}}"
"""
        elif func.startswith(('process_', 'transform_', 'convert_', 'parse_')):
            # Data processing function
            test_content += f"""
    @pytest.mark.parametrize("input_value,expected", [
        ("valid input", "processed result"),  # Valid input
        ("", None),  # Empty input
        (None, None),  # None input
        # Add more test cases as needed
    ])
    def test_{func}_processes_data(self, input_value, expected):
        \"\"\"Test {func} correctly processes data.\"\"\"
        # Arrange - set up any mocks or fixtures
        
        # Act
        result = {func}(input_value)
        
        # Assert
        assert result == expected, f"Expected {{expected}} but got {{result}}"
        
    def test_{func}_handles_edge_cases(self):
        \"\"\"Test {func} handles edge cases appropriately.\"\"\"
        # Test with large input
        large_input = "x" * 10000
        # Test with special characters
        special_input = "!@#$%^&*()"
        
        # Verify no exceptions are raised and results are as expected
        try:
            {func}(large_input)
            {func}(special_input)
            self.assertTrue(True)  # If we get here without exceptions, the test passes
        except Exception as e:
            self.fail(f"Function raised an exception with edge case input: {{e}}")
"""
        else:
            # Generate intelligent test cases based on function name
            test_cases = _generate_intelligent_test_cases(func, param_names)
            test_case_str = _generate_parametrized_test_case_string(func, test_cases)
            
            # General function with smarter test cases
            test_content += f"""
    @pytest.mark.parametrize("inputs,expected", [
{test_case_str}
    ])
    def test_{func}_parametrized(self, inputs, expected):
        \"\"\"Test {func} with multiple scenarios.\"\"\"
        # Arrange - set up any mocks or fixtures
        
        # Act
        result = {func}(**inputs)
        
        # Assert
        assert result == expected, f"Expected {{expected}} but got {{result}}"
        
    def test_{func}_raises_appropriate_exceptions(self):
        \"\"\"Test {func} raises appropriate exceptions for invalid inputs.\"\"\"
        # Arrange - prepare invalid inputs that should raise exceptions
        invalid_inputs = [
            # Add invalid inputs that should cause exceptions
            {{"type": "invalid type", "value": object(), "expected_exception": TypeError}},
            {{"type": "out of range", "value": -1, "expected_exception": ValueError}},
        ]
        
        # Act & Assert
        for test_case in invalid_inputs:
            with self.subTest(f"Testing {{test_case['type']}}"):
                with self.assertRaises(test_case['expected_exception']):
                    {func}(test_case['value'])
"""

    # Fallback: if no classes or functions found, add a simple existence test.
    if not module_info['content'].get('classes') and not module_info['content'].get('functions'):
        test_content += """
    def test_module_exists(self):
        \"\"\"Test that the module exists.\"\"\"
        self.assertTrue(True)
"""
    
    # Add module level tests
    test_content += """
    def test_module_constants(self):
        \"\"\"Test module level constants have expected values.\"\"\"
        # Check important module constants
        # Update these assertions with actual constants from your module
        # Example: self.assertEqual(MODULE_NAME.CONSTANT_NAME, expected_value)
        pass

    def test_module_imports(self):
        \"\"\"Test all required dependencies are available.\"\"\"
        # This test verifies the module can import all its dependencies
        # If we got this far without import errors, the test passes
        self.assertTrue(True)
"""
    
    test_content += """
if __name__ == '__main__':
    unittest.main()
"""
    return test_content

def _generate_retrieval_test(cls_name, method):
    """Generate test for retrieval methods."""
    return f"""
    def test_{method}_retrieves_data(self):
        \"\"\"Test that {cls_name}.{method} correctly retrieves data.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        expected_data = {{"id": "test_id", "data": "test_data"}}  # More realistic expected value
        
        # If this is a database or external retrieval, mock the source
        # Example: with patch('some_module.some_function') as mock_function:
        #     mock_function.return_value = expected_data
        
        # Act
        try:
            # Try different parameter patterns based on common method signatures
            if "{method}" in ["get_by_id", "get_item", "find_by_id"]:
                result = instance.{method}("test_id")
            elif "{method}" in ["get_all", "list_all", "fetch_all"]:
                result = instance.{method}()
                expected_data = [expected_data]  # Expect a list for get_all type methods
            elif "{method}".endswith("_by_name"):
                result = instance.{method}("test_name")
            else:
                # Default approach for other retrieval methods
                result = instance.{method}("test_id")
            
            # Assert
            self.assertEqual(result, expected_data)
            # Add more specific assertions for complex objects
            if isinstance(result, dict):
                for key in expected_data:
                    self.assertIn(key, result, f"Key {{key}} should be in result")
        except Exception as e:
            self.fail(f"Method raised an exception: {{e}}")
"""

def _generate_setter_test(cls_name, method):
    """Generate test for setter methods."""
    return f"""
    def test_{method}_updates_state(self):
        \"\"\"Test that {cls_name}.{method} correctly updates state.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Determine appropriate test values based on method name
        if "{method}".endswith("_name"):
            test_value = "new_name"
            property_name = "name"
        elif "{method}".endswith("_status"):
            test_value = "active"
            property_name = "status"
        elif "{method}".endswith("_config"):
            test_value = {{"setting": True}}
            property_name = "config"
        else:
            test_value = "test_value"
            property_name = "{method}".replace("set_", "")
        
        # Act
        try:
            # Try to set the value
            result = instance.{method}(test_value)
            
            # Assert - check the result if method returns a value
            if result is not None:
                if isinstance(result, bool):
                    self.assertTrue(result, "Setter should return True on success")
                
            # Check that state was updated through a getter if available
            getter_name = "{method}".replace("set_", "get_")
            if hasattr(instance, getter_name) and callable(getattr(instance, getter_name)):
                updated_value = getattr(instance, getter_name)()
                self.assertEqual(updated_value, test_value, f"Value should be updated to {{test_value}}")
            
            # Or through a property if available
            elif hasattr(instance, property_name):
                self.assertEqual(getattr(instance, property_name), test_value, f"Property {{property_name}} should be updated")
                
        except Exception as e:
            self.fail(f"Method raised an exception: {{e}}")
        
    def test_{method}_validates_input(self):
        \"\"\"Test that {cls_name}.{method} validates inputs properly.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        invalid_values = [None]
        
        # Add type-specific invalid values
        if "{method}".endswith(("_count", "_size", "_limit")):
            invalid_values.extend([-1, "not_a_number"])
        elif "{method}".endswith(("_date", "_time")):
            invalid_values.extend(["not_a_date", 12345])
        
        # Act & Assert
        for invalid_value in invalid_values:
            with self.subTest(f"Testing with {{invalid_value}}"):
                try:
                    result = instance.{method}(invalid_value)
                    # If no exception, should at least return False or None to indicate failure
                    self.assertIn(result, [False, None], f"Method should indicate failure for invalid input {{invalid_value}}")
                except Exception as e:
                    # An exception is also acceptable for invalid input
                    self.assertIsInstance(e, (ValueError, TypeError, AttributeError), 
                                        f"Expected ValueError, TypeError or AttributeError, got {{type(e).__name__}}")
"""

def _generate_creation_test(cls_name, method):
    """Generate test for creation methods."""
    return f"""
    def test_{method}_creates_correctly(self):
        \"\"\"Test that {cls_name}.{method} correctly creates the expected object.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Determine appropriate parameters based on method name
        if "{method}".startswith("create_user"):
            input_params = {{"username": "test_user", "email": "test@example.com"}}
            expected_type = "User"  # Expected return type
        elif "{method}".startswith(("create_item", "add_item")):
            input_params = {{"name": "test_item", "value": 42}}
            expected_type = "Item"
        elif "{method}".startswith("create_config"):
            input_params = {{"name": "test_config", "settings": {{"enabled": True}}}}
            expected_type = "Config"
        else:
            # Default parameters for generic creation methods
            input_params = {{"name": "test_object", "description": "A test object"}}
            expected_type = "Object"
        
        # Act
        try:
            result = instance.{method}(**input_params)
            
            # Assert
            self.assertIsNotNone(result, "Method should return a created object")
            
            # Check if result has expected properties
            for key, value in input_params.items():
                if hasattr(result, key):
                    self.assertEqual(getattr(result, key), value, f"Property {{key}} should match input")
                elif isinstance(result, dict):
                    self.assertEqual(result.get(key), value, f"Dictionary key {{key}} should match input")
            
            # Check if result is of expected type (if applicable)
            if expected_type != "Object" and hasattr(result, "__class__"):
                self.assertIn(expected_type, result.__class__.__name__, 
                            f"Result should be of type {{expected_type}}")
                
        except Exception as e:
            self.fail(f"Method raised an exception: {{e}}")
        
    def test_{method}_handles_invalid_input(self):
        \"\"\"Test that {cls_name}.{method} handles invalid input appropriately.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Define several invalid inputs to test
        invalid_inputs = [
            {{}},  # Empty dict
            None,  # None value
            {{"invalid_param": "value"}}  # Wrong parameter name
        ]
        
        # Act & Assert
        for invalid_input in invalid_inputs:
            with self.subTest(f"Testing with {{invalid_input}}"):
                try:
                    if invalid_input is None:
                        result = instance.{method}(None)
                    elif isinstance(invalid_input, dict):
                        result = instance.{method}(**invalid_input)
                    else:
                        result = instance.{method}(invalid_input)
                        
                    # If no exception, verify the result indicates failure
                    self.assertIn(result, [None, False, {{}}, []], 
                                f"Method should return None, False, empty dict/list for invalid input")
                except Exception as e:
                    # If an exception is raised, it should be an appropriate type
                    self.assertIsInstance(e, (ValueError, TypeError, AttributeError), 
                                        f"Expected ValueError, TypeError or AttributeError, got {{type(e).__name__}}")
"""

def _generate_deletion_test(cls_name, method):
    """Generate test for deletion methods."""
    return f"""
    def test_{method}_removes_correctly(self):
        \"\"\"Test that {cls_name}.{method} correctly removes the item.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Determine appropriate test scenario based on method name
        if "{method}".endswith(("_by_id", "_item")):
            test_id = "test_id"
            # Setup: add an item that can be deleted
            # This could be mocked or use a setup method
        elif "{method}".endswith("_all"):
            test_id = None  # No ID needed for delete_all
            # Setup: ensure there are items to delete
        else:
            test_id = "test_id"  # Default ID
        
        # Setup mock for verification if applicable
        # with patch.object(instance, 'has_item') as mock_has_item:
        #     mock_has_item.return_value = True  # Item exists before deletion
        
        # Act
        try:
            if test_id is None:
                result = instance.{method}()  # For delete_all type methods
            else:
                result = instance.{method}(test_id)
            
            # Assert
            self.assertTrue(result, "Deletion should return True for success")
            
            # Verify the item no longer exists if there's a way to check
            # For example, if there's a has_item or get_item method
            if hasattr(instance, 'has_item') and callable(getattr(instance, 'has_item')):
                self.assertFalse(instance.has_item(test_id), "Item should no longer exist after deletion")
            elif hasattr(instance, 'get_item') and callable(getattr(instance, 'get_item')):
                with self.assertRaises(Exception):
                    instance.get_item(test_id)  # Should raise an exception for non-existent item
                    
        except Exception as e:
            self.fail(f"Method raised an exception: {{e}}")
        
    def test_{method}_handles_nonexistent_item(self):
        \"\"\"Test that {cls_name}.{method} handles nonexistent items gracefully.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        nonexistent_id = "nonexistent_id"  # ID that doesn't exist
        
        # Setup mock to simulate nonexistent item
        # with patch.object(instance, 'has_item') as mock_has_item:
        #     mock_has_item.return_value = False  # Item doesn't exist
        
        # Act & Assert
        try:
            result = instance.{method}(nonexistent_id)
            # If no exception, the method should indicate failure
            self.assertFalse(result, "Should return False for nonexistent item")
        except Exception as e:
            # If exception is expected behavior, verify it's the right type
            self.assertIsInstance(e, (ValueError, KeyError, LookupError), 
                                f"Expected ValueError, KeyError or LookupError, got {{type(e).__name__}}")
"""

def _generate_validation_test(cls_name, method):
    """Generate test for validation methods."""
    return f"""
    def test_{method}_valid_cases(self):
        \"\"\"Test that {cls_name}.{method} returns True for valid cases.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Define test cases based on validation method type
        if "{method}".startswith("is_valid"):
            valid_cases = [
                {{"input": "valid_value", "name": "Standard valid input"}},
                {{"input": "valid_with_spaces", "name": "Input with spaces"}},
                {{"input": "123456", "name": "Numeric input"}},
            ]
        elif "{method}".startswith(("is_", "has_")):
            # For boolean check methods
            valid_cases = [
                {{"input": True, "name": "Boolean true"}},
                {{"input": "value", "name": "Non-empty string"}},
                {{"input": 42, "name": "Non-zero number"}},
                {{"input": ["item"], "name": "Non-empty list"}},
            ]
        else:
            # Default validation cases
            valid_cases = [
                {{"input": "test_value", "name": "Standard valid input"}},
                {{"input": 42, "name": "Numeric input"}},
            ]
        
        # Act & Assert
        for case in valid_cases:
            with self.subTest(f"Testing {{case['name']}}"):
                try:
                    result = instance.{method}(case["input"])
                    self.assertTrue(result, f"Should return True for {{case['name']}}")
                except Exception as e:
                    self.fail(f"Method raised an exception for valid input {{case['name']}}: {{e}}")
        
    def test_{method}_invalid_cases(self):
        \"\"\"Test that {cls_name}.{method} returns False for invalid cases.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Define invalid test cases based on validation method type
        if "{method}".startswith("is_valid"):
            invalid_cases = [
                {{"input": "", "name": "Empty string"}},
                {{"input": None, "name": "None value"}},
                {{"input": "@#$%", "name": "Special characters only"}},
                {{"input": "a" * 1000, "name": "Too long input"}},
            ]
        elif "{method}".startswith(("is_", "has_")):
            # For boolean check methods
            invalid_cases = [
                {{"input": False, "name": "Boolean false"}},
                {{"input": "", "name": "Empty string"}},
                {{"input": 0, "name": "Zero value"}},
                {{"input": [], "name": "Empty list"}},
                {{"input": None, "name": "None value"}},
            ]
        else:
            # Default invalid cases
            invalid_cases = [
                {{"input": None, "name": "None value"}},
                {{"input": "", "name": "Empty string"}},
                {{"input": -1, "name": "Negative number"}},
            ]
        
        # Act & Assert
        for case in invalid_cases:
            with self.subTest(f"Testing {{case['name']}}"):
                try:
                    result = instance.{method}(case["input"])
                    self.assertFalse(result, f"Should return False for {{case['name']}}")
                except Exception as e:
                    # Some validation methods might raise exceptions for invalid input
                    # This is also acceptable behavior
                    self.assertIsInstance(e, (ValueError, TypeError, AttributeError), 
                                        f"Expected ValueError, TypeError or AttributeError for {{case['name']}}, got {{type(e).__name__}}")
"""

def _generate_processing_test(cls_name, method):
    """Generate test for processing methods."""
    return f"""
    def test_{method}_processes_data_correctly(self):
        \"\"\"Test that {cls_name}.{method} processes data correctly.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Define test scenarios based on processing method type
        if "{method}".startswith(("process_", "handle_")):
            test_input = {{"data": "raw_data", "options": {{"option1": True}}}}
            expected_output = {{"processed": True, "result": "processed_data"}}
        elif "{method}".startswith("transform_"):
            test_input = "input_format"
            expected_output = "transformed_format"
        elif "{method}".startswith("calculate_"):
            test_input = [1, 2, 3, 4, 5]
            expected_output = 15  # Sum or some calculation
        else:
            # Default processing scenario
            test_input = "test_input"
            expected_output = "processed_output"
        
        # Mock any dependencies called by the method
        # with patch.object(instance, '_internal_helper') as mock_helper:
        #     mock_helper.return_value = some_intermediate_value
        
        # Act
        try:
            # Call with appropriate parameters based on input type
            if isinstance(test_input, dict):
                if "data" in test_input and "options" in test_input:
                    result = instance.{method}(test_input["data"], **test_input["options"])
                else:
                    result = instance.{method}(**test_input)
            else:
                result = instance.{method}(test_input)
            
            # Assert
            if isinstance(expected_output, dict):
                for key, value in expected_output.items():
                    self.assertIn(key, result)
                    self.assertEqual(result[key], value)
            else:
                self.assertEqual(result, expected_output)
                
        except Exception as e:
            self.fail(f"Method raised an exception: {{e}}")
        
    def test_{method}_handles_errors(self):
        \"\"\"Test that {cls_name}.{method} handles errors appropriately.\"\"\"
        # Arrange
        instance = self._create_test_{cls_name.lower()}()
        
        # Define error-triggering inputs based on processing method type
        if "{method}".startswith(("process_", "handle_")):
            error_input = {{"malformed": "data"}}  # Missing required fields
        elif "{method}".startswith("transform_"):
            error_input = None  # Null input
        elif "{method}".startswith("calculate_"):
            error_input = ["not", "a", "number"]  # Non-numeric data for calculation
        else:
            # Default error input
            error_input = None  # Null is a common edge case
        
        # Setup mock to simulate an error if testing error handling of dependencies
        # with patch.object(instance, '_internal_helper') as mock_helper:
        #     mock_helper.side_effect = Exception("Simulated dependency error")
        
        # Act & Assert
        try:
            # Try to process the error-triggering input
            if isinstance(error_input, dict):
                result = instance.{method}(**error_input)
            else:
                result = instance.{method}(error_input)
                
            # If no exception, check that result indicates error/failure
            if result is not None:
                if isinstance(result, dict) and "error" in result:
                    self.assertTrue(result["error"], "Result should indicate an error")
                elif isinstance(result, bool):
                    self.assertFalse(result, "Result should be False for error input")
            
        except Exception as e:
            # If expected to propagate exceptions, verify it's a reasonable type
            self.assertIsInstance(e, (ValueError, TypeError, AttributeError, KeyError),
                                f"Expected ValueError, TypeError, AttributeError or KeyError, got {{type(e).__name__}}")
"""

def generate_test_with_ollama(module_path):
    """Generate a test file using Ollama."""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        ollama_cmd = "ollama run deepseek-r1"
        prompt = f"""Generate a comprehensive pytest test file for this Python module.
Include tests for all public methods and functions with appropriate mocks and fixtures.
Focus on edge cases and error conditions. Return ONLY the complete test code.

```python
{source_code}
```"""
        cmd = ollama_cmd.split()
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600
        )
        output = result.stdout.strip()
        if "```python" in output and "```" in output:
            start = output.find("```python") + len("```python")
            end = output.rfind("```")
            if start < end:
                code = output[start:end].strip()
                return code
        return output
    except subprocess.TimeoutExpired:
        return "# Error: Ollama call timed out."
    except Exception as e:
        return f"# Error generating test: {str(e)}"

def format_with_black(file_path: Path):
    """Run Black to format the given file."""
    try:
        subprocess.run(["black", str(file_path)], stdout=subprocess.DEVNULL, check=True)
    except Exception as e:
        print(f"Warning: Black formatting failed for {file_path}: {e}")

def create_test_file(module_info, use_ollama=False):
    """Create a test file for a module and format it."""
    module_path = module_info['path']
    test_filename = module_to_test_filename(module_path)
    # Create test directory matching module's subdirectory structure if needed.
    if module_info['relative_path'].parts[0] == "chat_mate":
        subdir = Path(*module_info['relative_path'].parts[1:-1])
        test_dir = TEST_DIR / subdir
    else:
        test_dir = TEST_DIR
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / test_filename

    # Use cache to avoid regenerating tests too often.
    cache = load_cache()
    last_gen = cache.get(module_info['name'], {}).get("generated_at")
    regenerate = True
    if last_gen:
        last_time = datetime.fromisoformat(last_gen)
        delta = datetime.utcnow() - last_time
        if delta.total_seconds() < 300:
            regenerate = False
            print(f"Skipping regeneration for {module_info['name']} (generated {delta.total_seconds():.0f}s ago)")

    if regenerate:
        if use_ollama:
            test_content = generate_test_with_ollama(module_path)
        else:
            test_content = generate_test_template(module_info)
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        format_with_black(test_file)
        # Update cache.
        cache[module_info['name']] = {
            "file": str(test_file),
            "generated_at": datetime.utcnow().isoformat()
        }
        save_cache(cache)
        print(f"Created {test_file}")
    else:
        print(f"Test file already up-to-date: {test_file}")

    return test_file

def run_tests(test_files):
    """Run pytest on the generated test files."""
    if not test_files:
        return
    print(f"\nRunning tests on {len(test_files)} generated test file(s)...")
    cmd = ["pytest", "-v"] + [str(f) for f in test_files]
    subprocess.run(cmd, cwd=str(PROJECT_ROOT))

def _generate_intelligent_test_cases(func_name, param_names=None):
    """Generate intelligent test cases based on function name and parameters."""
    test_cases = []
    
    # Default parameter is a string if we don't know better
    if not param_names:
        param_names = ["input"]
    
    # Generate test cases based on function name patterns
    if any(func_name.startswith(prefix) for prefix in ['get_', 'fetch_', 'retrieve_', 'find_', 'load_']):
        # Data retrieval function
        test_cases = [
            {"id": "happy_path", "inputs": {"id": "valid_id"}, "expected": {"id": "valid_id", "data": "sample_data"}},
            {"id": "empty_input", "inputs": {"id": ""}, "expected": None},
            {"id": "none_input", "inputs": {"id": None}, "expected": None},
            {"id": "invalid_id", "inputs": {"id": "invalid_id"}, "expected": {}}
        ]
    elif any(func_name.startswith(prefix) for prefix in ['validate_', 'is_', 'has_', 'check_', 'can_']):
        # Validation function
        test_cases = [
            {"id": "valid_input", "inputs": {"value": "valid_data"}, "expected": True},
            {"id": "invalid_input", "inputs": {"value": "invalid_data"}, "expected": False},
            {"id": "edge_case", "inputs": {"value": ""}, "expected": False},
            {"id": "none_input", "inputs": {"value": None}, "expected": False}
        ]
    elif any(func_name.startswith(prefix) for prefix in ['process_', 'transform_', 'convert_', 'parse_']):
        # Processing function
        test_cases = [
            {"id": "standard_input", "inputs": {"data": "raw_data"}, "expected": "processed_data"},
            {"id": "empty_input", "inputs": {"data": ""}, "expected": ""},
            {"id": "complex_input", "inputs": {"data": {"nested": "structure"}}, "expected": "processed_nested_structure"},
            {"id": "none_input", "inputs": {"data": None}, "expected": None}
        ]
    elif any(func_name.startswith(prefix) for prefix in ['create_', 'add_', 'insert_', 'new_']):
        # Creation function
        test_cases = [
            {"id": "valid_creation", "inputs": {"name": "test_item", "value": 42}, "expected": {"id": 1, "name": "test_item", "value": 42}},
            {"id": "minimal_input", "inputs": {"name": "minimal"}, "expected": {"id": 2, "name": "minimal"}},
            {"id": "with_options", "inputs": {"name": "with_options", "options": {"flag": True}}, "expected": {"id": 3, "name": "with_options", "options": {"flag": True}}},
            {"id": "invalid_input", "inputs": {"name": ""}, "expected": None}
        ]
    elif any(func_name.startswith(prefix) for prefix in ['delete_', 'remove_', 'drop_']):
        # Deletion function
        test_cases = [
            {"id": "existing_item", "inputs": {"id": 1}, "expected": True},
            {"id": "nonexistent_item", "inputs": {"id": 999}, "expected": False},
            {"id": "invalid_id", "inputs": {"id": None}, "expected": False},
            {"id": "with_options", "inputs": {"id": 2, "force": True}, "expected": True}
        ]
    elif any(func_name.startswith(prefix) for prefix in ['update_', 'modify_', 'change_', 'set_']):
        # Update function
        test_cases = [
            {"id": "valid_update", "inputs": {"id": 1, "value": "new_value"}, "expected": True},
            {"id": "nonexistent_id", "inputs": {"id": 999, "value": "any"}, "expected": False},
            {"id": "no_change", "inputs": {"id": 2, "value": "same_value"}, "expected": True},
            {"id": "invalid_input", "inputs": {"id": None, "value": None}, "expected": False}
        ]
    elif any(func_name.startswith(prefix) for prefix in ['calculate_', 'compute_', 'sum_', 'count_']):
        # Calculation function
        test_cases = [
            {"id": "simple_calc", "inputs": {"values": [1, 2, 3]}, "expected": 6},
            {"id": "empty_input", "inputs": {"values": []}, "expected": 0},
            {"id": "negative_values", "inputs": {"values": [-1, -2, 3]}, "expected": 0},
            {"id": "large_values", "inputs": {"values": [1000, 2000]}, "expected": 3000}
        ]
    elif any(func_name.startswith(prefix) for prefix in ['filter_', 'select_', 'query_']):
        # Filtering function
        test_cases = [
            {"id": "matching_items", "inputs": {"criteria": "matching"}, "expected": ["item1", "item2"]},
            {"id": "no_matches", "inputs": {"criteria": "nomatch"}, "expected": []},
            {"id": "all_items", "inputs": {"criteria": None}, "expected": ["item1", "item2", "item3"]},
            {"id": "complex_criteria", "inputs": {"criteria": {"field": "value"}}, "expected": ["item3"]}
        ]
    else:
        # Generic function - provide reasonable defaults
        test_cases = [
            {"id": "standard_case", "inputs": {"input": "test_value"}, "expected": "result"},
            {"id": "edge_case", "inputs": {"input": ""}, "expected": ""},
            {"id": "null_case", "inputs": {"input": None}, "expected": None},
            {"id": "special_chars", "inputs": {"input": "!@#$%^"}, "expected": "processed_special_chars"}
        ]
    
    # Adjust input keys based on actual parameter names if available
    if param_names:
        updated_cases = []
        for case in test_cases:
            # Get the values from existing inputs
            values = list(case["inputs"].values())
            # Create new inputs dict with actual parameter names
            new_inputs = {}
            for i, param in enumerate(param_names):
                if i < len(values):
                    new_inputs[param] = values[i]
                else:
                    # Add a default value if we have more parameters than values
                    new_inputs[param] = "default_value"
            # Update the test case
            case["inputs"] = new_inputs
            updated_cases.append(case)
        test_cases = updated_cases
    
    return test_cases

def _generate_parametrized_test_case_string(func, test_cases):
    """Generate parametrized test cases as a formatted string."""
    case_lines = []
    
    for case in test_cases:
        # Format the inputs and expected values
        inputs_str = ", ".join([f"{k}={repr(v)}" for k, v in case["inputs"].items()])
        expected_str = repr(case["expected"])
        case_lines.append(f"        # {case['id']}")
        case_lines.append(f"        ({{{inputs_str}}}, {expected_str}),")
    
    return "\n".join(case_lines)

def main():
    args = parse_args()
    print("Finding Python modules...")
    modules = find_python_modules()
    print("Finding existing tests...")
    existing_tests = find_existing_tests()

    modules_without_tests = []
    print("\nAnalyzing modules for testability...")
    for module in modules:
        # Use consistent mapping from module path to test file name.
        test_filename = module_to_test_filename(module['path'])
        if test_filename in existing_tests:
            continue
        if args.module and not module['name'].startswith(args.module):
            continue
        content = analyze_module_content(module['path'])
        total_methods = sum(len(cls.get('methods', [])) for cls in content.get('classes', []))
        total_methods += len(content.get('functions', []))
        if content.get('needs_test', False) and total_methods >= args.min_methods:
            module['content'] = content
            module['total_methods'] = total_methods
            modules_without_tests.append(module)

    print(f"\nFound {len(modules_without_tests)} modules without tests:")
    for i, module in enumerate(modules_without_tests, 1):
        print(f"{i}. {module['name']} ({module['total_methods']} testable methods)")

    if args.summary_only:
        return 0

    generated_files = []
    if args.auto_generate:
        print("\nGenerating test files...")
        for module in modules_without_tests:
            test_file = create_test_file(module, use_ollama=args.use_ollama)
            generated_files.append(test_file)
    else:
        print("\nTo generate test files, run with --auto-generate flag")

    if args.run_tests and generated_files:
        run_tests(generated_files)

    return 0

if __name__ == "__main__":
    sys.exit(main())
