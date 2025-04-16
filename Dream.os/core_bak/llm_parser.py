import re
import json
import os
import sys

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # core
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Up one level
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# --- Core Service Imports ---
try:
    from core.memory.governance_memory_engine import log_event
except ImportError:
    print("[LLMParser Error ❌] Failed to import governance_memory_engine. Using dummy logger.")
    def log_event(event_type, source, details): print(f"[Dummy Log] Event: {event_type}, Source: {source}, Details: {details}")
# ---------------------------

_SOURCE = "LLMParserUtil"

def extract_json_from_response(response_text: str) -> dict | list | None:
    """Extracts a JSON object or list from a string containing a markdown code block."""
    if not response_text or not isinstance(response_text, str):
        log_event("PARSE_INPUT_INVALID", _SOURCE, {"error": "Invalid input provided for JSON extraction", "input_type": type(response_text).__name__})
        return None

    # Regex to find JSON within ```json ... ``` blocks
    # Handles both objects {} and lists []
    json_match = re.search(r'```json\s*(\{.*?\}|\s*\[.*?\])\s*```', response_text, re.DOTALL | re.IGNORECASE)
    
    if json_match:
        json_str = json_match.group(1)
        try:
            parsed_json = json.loads(json_str)
            log_event("PARSE_JSON_SUCCESS", _SOURCE, {"status": "Successfully parsed JSON from response"})
            return parsed_json
        except json.JSONDecodeError as e:
            log_event("PARSE_JSON_ERROR", _SOURCE, {"error": "JSON decoding failed", "json_string": json_str, "details": str(e)})
            return None
    else:
        log_event("PARSE_JSON_NOT_FOUND", _SOURCE, {"warning": "Could not find JSON block in response text"})
        # Optional: Attempt to parse the entire string if no block found?
        # try:
        #     return json.loads(response_text)
        # except json.JSONDecodeError:
        #     pass
        return None

# --- Example Usage ---
if __name__ == "__main__":
    print("--- Testing LLM Parser Utility ---")

    test_string_1 = "Some text before\n```json\n{\"key\": \"value\", \"list\": [1, 2]}\n```\nSome text after."
    test_string_2 = "No JSON block here."
    test_string_3 = "```json\n[\"item1\", \"item2\"]\n```"
    test_string_4 = "```json\n{\"bad\": json\"}\n```" # Invalid JSON
    test_string_5 = "```json\n   {\"whitespace\": true}   \n```"
    test_string_6 = None
    test_string_7 = "```json\n{\"key\": \"value\"} # Comment outside block```"

    print("\nTest 1 (Valid Object):")
    result1 = extract_json_from_response(test_string_1)
    print(f"  -> Parsed: {result1}")
    assert isinstance(result1, dict)

    print("\nTest 2 (No JSON Block):")
    result2 = extract_json_from_response(test_string_2)
    print(f"  -> Parsed: {result2}")
    assert result2 is None

    print("\nTest 3 (Valid List):")
    result3 = extract_json_from_response(test_string_3)
    print(f"  -> Parsed: {result3}")
    assert isinstance(result3, list)

    print("\nTest 4 (Invalid JSON):")
    result4 = extract_json_from_response(test_string_4)
    print(f"  -> Parsed: {result4}")
    assert result4 is None

    print("\nTest 5 (Whitespace):")
    result5 = extract_json_from_response(test_string_5)
    print(f"  -> Parsed: {result5}")
    assert isinstance(result5, dict)
    
    print("\nTest 6 (None Input):")
    result6 = extract_json_from_response(test_string_6)
    print(f"  -> Parsed: {result6}")
    assert result6 is None

    print("\nTest 7 (Comment Outside Block):")
    result7 = extract_json_from_response(test_string_7)
    print(f"  -> Parsed: {result7}")
    assert isinstance(result7, dict)

    print("\n--- LLM Parser Test Complete --- ") 