"""Shared test data for LLM response parsing tests."""

# Sample JSON responses with different formats
SAMPLE_JSON_RESPONSES = {
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

# Sample code blocks in different languages
SAMPLE_CODE_RESPONSES = {
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

# Sample list formats
SAMPLE_LIST_RESPONSES = {
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

def create_test_response(response_type, format_type):
    """Create a test response of the specified type and format."""
    responses = {
        "json": SAMPLE_JSON_RESPONSES,
        "code": SAMPLE_CODE_RESPONSES,
        "list": SAMPLE_LIST_RESPONSES
    }
    return responses[response_type][format_type]

def validate_json_response(result, expected_data):
    """Validate JSON extraction results."""
    if expected_data is None:
        assert result is None
        return
    
    assert result is not None
    for key, value in expected_data.items():
        assert result[key] == value

def validate_code_response(result, expected_code, should_contain=None, should_not_contain=None):
    """Validate code extraction results."""
    if expected_code is None:
        assert result is None
        return
    
    assert result is not None
    if expected_code:
        assert result == expected_code
    if should_contain:
        assert should_contain in result
    if should_not_contain:
        assert should_not_contain not in result

def validate_list_response(result, expected_items=None, expected_length=None):
    """Validate list extraction results."""
    if expected_items is None and expected_length is None:
        assert result == []
        return
    
    if expected_length is not None:
        assert len(result) == expected_length
    
    if expected_items:
        for item in expected_items:
            assert item in result 