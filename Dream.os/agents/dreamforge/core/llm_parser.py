"""Parser utilities for LLM responses."""
import json
import re
from typing import Dict, Any, Optional

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from an LLM response."""
    try:
        # Try to find JSON between triple backticks
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            return json.loads(json_str)
            
        # Try to find JSON between curly braces
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
            
        # Try to parse the entire response as JSON
        return json.loads(response)
    except Exception as e:
        print(f"Error extracting JSON: {e}")
        return None
        
def extract_code_from_response(response: str, language: str = None) -> Optional[str]:
    """Extract code from an LLM response."""
    try:
        # Try to find code between triple backticks
        if language:
            pattern = f'```{language}\s*(.*?)\s*```'
        else:
            pattern = r'```(?:\w+)?\s*(.*?)\s*```'
            
        code_match = re.search(pattern, response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
            
        return None
    except Exception as e:
        print(f"Error extracting code: {e}")
        return None
        
def extract_list_from_response(response: str) -> list:
    """Extract a list from an LLM response."""
    try:
        # Try to find list items with bullet points or numbers
        items = re.findall(r'(?:^|\n)[-*\d+.]\s*(.*?)(?=\n|$)', response)
        if items:
            return [item.strip() for item in items]
            
        # Try to parse as JSON list
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
            
        return []
    except Exception as e:
        print(f"Error extracting list: {e}")
        return [] 