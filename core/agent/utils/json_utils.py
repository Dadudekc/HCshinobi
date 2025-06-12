"""JSON parsing and validation utilities."""
import json
from typing import Dict, Any, Tuple, Optional

def extract_json_from_text(text: str) -> str:
    """Extract JSON content from a text string."""
    if not text:
        raise ValueError("Empty text provided")
        
    json_start = text.find("{")
    json_end = text.rfind("}") + 1
    if json_start == -1 or json_end <= json_start:
        raise ValueError("No valid JSON object found in text")
    return text[json_start:json_end]

def safe_json_loads(text: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """Safely load JSON from text, handling common errors.
    
    Args:
        text: String containing JSON data, possibly embedded in other text
        
    Returns:
        Tuple of (parsed_data, error_message)
        If successful, error_message will be None
    """
    if not text:
        return {}, "Empty text provided"
        
    try:
        # Try to extract JSON if embedded in text
        json_str = extract_json_from_text(text)
        data = json.loads(json_str)
        return data, None
    except ValueError as e:
        return {}, f"Invalid JSON format: {e}"
    except json.JSONDecodeError as e:
        return {}, f"JSON decode error: {e}"
    except Exception as e:
        return {}, f"Unexpected error parsing JSON: {e}" 