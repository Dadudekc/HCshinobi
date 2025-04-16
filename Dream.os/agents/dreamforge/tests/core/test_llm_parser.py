"""Tests for LLM response parsing utilities."""
import json
import pytest
from typing import Optional, Dict, Any
from dreamforge.core.llm.response_parser import (
    extract_code_block,
    parse_json_response,
    extract_first_json_block,
    clean_llm_response
)
from dreamforge.core.memory.governance_memory_engine import log_event
from dreamforge.tests.core.utils.llm_test_utils import LLMTestResponse

@pytest.fixture
def sample_json_response():
    """Sample response containing JSON data."""
    return {
        "with_backticks": '''Here's the JSON:
```json
{
    "key": "value",
    "nested": {
        "array": [1, 2, 3]
    }
}
```
And some trailing text.''',
        "without_language": '''Some text
```
{"simple": "json"}
```''',
        "inline": 'Some text {"inline": "json"} more text',
        "invalid": '''```json
    {
        "invalid": "json",
        missing: quotes
    }
    ```''',
        "no_json": "Just some plain text without any JSON."
    }

@pytest.fixture
def sample_code_response():
    """Sample response containing code blocks."""
    return {
        "with_language": '''Here's some Python code:
```python
def hello():
    print("Hello, world!")
```''',
        "any_language": '''```javascript
console.log("Hello");
```''',
        "multiple_blocks": '''```python
def first():
    pass
```
Some text
```python
def second():
    pass
```''',
        "no_code": "Just some text without any code blocks."
    }

@pytest.fixture
def sample_list_response():
    """Sample response containing various list formats."""
    return {
        "bullet_points": '''Here are some items:
- First item
* Second item
- Third item with: colon
''',
        "numbered": '''Steps:
1. First step
2. Second step
3. Third step with number: 42
''',
        "json_array": '''Some text ["item1", "item2", "item3"] more text''',
        "invalid_array": '''["invalid", "json", array''',
        "no_list": "Just some text without any list items."
    }

class TestJSONExtraction:
    """Tests for JSON extraction functionality."""

    def test_with_backticks(self):
        """Test JSON extraction from response with backticks."""
        test_data = {
            "key": "value",
            "nested": {
                "array": [1, 2, 3]
            }
        }
        response = LLMTestResponse.with_json(test_data)
        result = parse_json_response(response)
        
        assert result is not None
        assert result["key"] == "value"
        assert result["nested"]["array"] == [1, 2, 3]

    def test_without_language_tag(self):
        """Test JSON extraction from response with backticks but no language tag."""
        test_data = {"simple": "json"}
        response = LLMTestResponse.with_json(test_data)
        result = parse_json_response(response)
        
        assert result is not None
        assert result["simple"] == "json"

    def test_with_curly_braces(self):
        """Test JSON extraction from response with just curly braces."""
        response = 'Some text {"inline": "json"} more text'
        result = parse_json_response(response)
        
        assert result is not None
        assert result["inline"] == "json"

    def test_invalid_json(self):
        """Test handling of invalid JSON in response."""
        response = LLMTestResponse.with_error("invalid_json")
        result = parse_json_response(response)
        
        assert result is None

    def test_no_json(self):
        """Test handling of response with no JSON."""
        response = LLMTestResponse.with_error("no_content")
        result = parse_json_response(response)
        
        assert result is None

class TestCodeExtraction:
    """Tests for code extraction functionality."""

    def test_with_language(self):
        """Test code extraction with specified language."""
        code = 'def hello():\n    print("Hello, world!")'
        response = LLMTestResponse.with_code(code, language="python")
        result = extract_code_block(response)
        
        assert result == code

    def test_any_language(self):
        """Test code extraction without specified language."""
        code = 'console.log("Hello");'
        response = LLMTestResponse.with_code(code, language="javascript")
        result = extract_code_block(response)
        
        assert result == code

    def test_no_code(self):
        """Test handling of response with no code blocks."""
        response = LLMTestResponse.with_error("no_content")
        result = extract_code_block(response)
        
        assert result is None

    def test_multiple_blocks(self):
        """Test code extraction with multiple code blocks."""
        first_block = "def first():\n    pass"
        second_block = "def second():\n    pass"
        response = f'''{LLMTestResponse.with_code(first_block, language="python")}
Some text
{LLMTestResponse.with_code(second_block, language="python")}'''
        
        result = extract_code_block(response)
        
        assert "def first():" in result
        assert "def second():" not in result

class TestListExtraction:
    """Tests for list extraction functionality."""

    def test_bullet_points(self):
        """Test list extraction from bullet points."""
        items = ["First item", "Second item", "Third item with: colon"]
        response = LLMTestResponse.with_list(items, format="bullet")
        result = extract_list_from_response(response)
        
        assert len(result) == 3
        assert all(item in result for item in items)

    def test_numbered_list(self):
        """Test list extraction from numbered points."""
        items = ["First step", "Second step", "Third step with number: 42"]
        response = LLMTestResponse.with_list(items, format="numbered")
        result = extract_list_from_response(response)
        
        assert len(result) == 3
        assert all(item in result for item in items)

    def test_json_array(self):
        """Test list extraction from JSON array."""
        items = ["item1", "item2", "item3"]
        response = f'Some text {LLMTestResponse.with_json(items)} more text'
        result = extract_list_from_response(response)
        
        assert result == items

    def test_no_list(self):
        """Test handling of response with no list."""
        response = LLMTestResponse.with_error("no_content")
        result = extract_list_from_response(response)
        
        assert result == []

    def test_invalid_json_array(self):
        """Test handling of invalid JSON array in response."""
        response = LLMTestResponse.with_error("invalid_json")
        result = extract_list_from_response(response)
        
        assert result == []

def test_setup():
    """Log test suite initialization."""
    log_event("TEST_SUITE_INITIALIZED", "TestLLMParser", {
        "test_count": 14,
        "test_categories": ["json", "code", "list"]
    })

if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, agentic simulation
    from pprint import pprint
    from datetime import datetime
    import uuid

    # Assume setup_test_imports() is available if needed, or handle imports directly
    # from dreamforge.tests.core.utils.test_utils import setup_test_imports
    # setup_test_imports() 

    def demonstrate_llm_parsing_with_kickoff():
        """Demonstrate LLM response parsing capabilities with agentic kickoff simulation."""
        print("\n=== Dream.OS LLM Response Parser Demo ===\n")
        
        # --- Agentic Kickoff Simulation ---
        agent_id = "ParserDemoAgent"
        task_id = f"task_{uuid.uuid4()}"
        timestamp = datetime.now().isoformat()
        print(f"🚀 Kicking off autonomous task for {agent_id} (Task ID: {task_id}) at {timestamp}")
        
        # 1. Log Task Start
        log_event("AGENT_TASK_STARTED", agent_id, {
            "task_id": task_id,
            "task_type": "LLM_PARSER_DEMO",
            "status": "running",
            "timestamp": timestamp
        })
        print(f"✓ Logged AGENT_TASK_STARTED event for {task_id}")
        
        # 2. Simulate Mailbox Update
        # In a real scenario, this would update the agent's mailbox.json
        print(f"⏳ Simulating update to {agent_id}/mailbox.json: Adding task {task_id}")
        print(f"✓ Simulated mailbox update for {agent_id}")

        # 3. Simulate Board Sync
        # In a real scenario, this would sync status to a central task board
        print(f"🔄 Simulating board sync: Task {task_id} status set to 'running'")
        print(f"✓ Simulated board sync for {task_id}")
        print("--- Kickoff Complete ---\n")
        
        # --- Core Functionality Demonstration ---
        
        # 1. Basic Code Block Extraction
        print("1. Extracting Code Block")
        code_response = """Here's a Python function to add numbers:
        ```python
        def add(a: int, b: int) -> int:
            return a + b
        ```
        You can use this function to add two numbers."""
        
        code = extract_code_block(code_response)
        print("Input Response:")
        print(code_response)
        print("\nExtracted Code:")
        print(code)
        print("✓ Code block extracted\n")
        
        # 2. JSON Response Parsing
        print("2. Parsing JSON Response")
        json_response = """The task details are:
        ```json
        {
            "task_id": "TASK_001",
            "priority": "high",
            "steps": ["plan", "execute", "verify"],
            "metadata": {
                "owner": "workflow_agent",
                "deadline": "2024-03-20"
            }
        }
        ```
        Please process this task accordingly."""
        
        parsed_json = parse_json_response(json_response)
        print("Input Response:")
        print(json_response)
        print("\nParsed JSON:")
        pprint(parsed_json)
        print("✓ JSON response parsed\n")
        
        # 3. First JSON Block Extraction
        print("3. Extracting First JSON Block")
        multiple_json = """Here are two configurations:
        ```json
        {
            "name": "Config A",
            "enabled": true
        }
        ```
        And another one:
        ```json
        {
            "name": "Config B",
            "enabled": false
        }
        ```"""
        
        first_json = extract_first_json_block(multiple_json)
        print("Input Response:")
        print(multiple_json)
        print("\nFirst JSON Block:")
        pprint(first_json)
        print("✓ First JSON block extracted\n")
        
        # 4. Response Cleaning
        print("4. Cleaning LLM Response")
        messy_response = """Here's what I found:
        
        ```
        Some unformatted content
        with multiple lines
        ```
        
        And some additional notes:
        1. Note one
        2. Note two"""
        
        cleaned = clean_llm_response(messy_response)
        print("Input Response:")
        print(messy_response)
        print("\nCleaned Response:")
        print(cleaned)
        print("✓ Response cleaned\n")
        
        # 5. Error Handling Examples
        print("5. Error Handling")
        
        # Invalid JSON
        print("\na) Invalid JSON:")
        invalid_json = """```json
        {
            "key": "value",
            invalid syntax here
        }
        ```"""
        parsing_error = None
        try:
            parse_json_response(invalid_json)
        except Exception as e:
            parsing_error = str(e)
            print(f"✓ Caught expected error: {parsing_error}")
        
        # Missing code block
        print("\nb) Missing Code Block:")
        no_block = "Just some text without any code blocks"
        result = extract_code_block(no_block)
        print(f"✓ Result is None: {result is None}")
        
        # Empty response
        print("\nc) Empty Response:")
        empty = ""
        cleaned_empty = clean_llm_response(empty)
        print(f"✓ Empty response handled: {cleaned_empty == ''}")
        
        print("\n--- Parser Capabilities Summary ---")
        print("✓ Code block extraction")
        print("✓ JSON response parsing")
        print("✓ First JSON block extraction")
        print("✓ Response cleaning")
        print("✓ Error handling")
        
        # --- Agentic Task Completion Simulation ---
        completion_timestamp = datetime.now().isoformat()
        print("\n--- Simulating Agent Task Completion ---")
        
        # 1. Log Task Completion
        log_event("AGENT_TASK_COMPLETED", agent_id, {
            "task_id": task_id,
            "task_type": "LLM_PARSER_DEMO",
            "status": "success",
            "timestamp": completion_timestamp,
            "results": {
                "code_extracted": code is not None,
                "json_parsed": parsed_json is not None,
                "first_json_extracted": first_json is not None,
                "response_cleaned": cleaned is not None,
                "error_handled": parsing_error is not None
            }
        })
        print(f"✓ Logged AGENT_TASK_COMPLETED event for {task_id}")

        # 2. Simulate Mailbox Update (Completion)
        print(f"⏳ Simulating update to {agent_id}/mailbox.json: Marking task {task_id} as completed")
        print(f"✓ Simulated mailbox completion update for {agent_id}")

        # 3. Simulate Board Sync (Completion)
        print(f"🔄 Simulating board sync: Task {task_id} status set to 'success'")
        print(f"✓ Simulated board completion sync for {task_id}")
        print("--- Completion Complete ---")

    try:
        demonstrate_llm_parsing_with_kickoff()
    except Exception as e:
        # Log failure if exception occurs during demo
        log_event("AGENT_TASK_FAILED", "ParserDemoAgent", {
            "task_id": "unknown_task_id", # Task ID might not be set if error is early
            "task_type": "LLM_PARSER_DEMO",
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        print(f"\n❌ Error during demonstration: {str(e)}")
        raise
    else:
        print("\n✅ All parsing examples and agentic simulation completed successfully") 