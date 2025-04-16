"""Service for staging and executing prompts through Cursor."""
import os
import json
import time
from typing import Dict, Any, Optional

from dreamforge.core import config
from dreamforge.core.template_engine import TemplateEngine

def render_prompt(template_name: str, context: Dict[str, Any]) -> str:
    """Render a prompt template with given context."""
    try:
        template_engine = TemplateEngine()
        return template_engine.render(template_name, context)
    except Exception as e:
        print(f"Error rendering prompt: {e}")
        return ""

def stage_prompt_for_cursor(template_name: str, context: Dict[str, Any]) -> bool:
    """Stage a rendered prompt for Cursor to process."""
    try:
        rendered = render_prompt(template_name, context)
        if not rendered:
            return False
            
        return write_to_cursor_input(rendered)
    except Exception as e:
        print(f"Error staging prompt: {e}")
        return False

def write_to_cursor_input(content: str, target_path: Optional[str] = None) -> bool:
    """Write content to the cursor input file."""
    try:
        path = target_path or config.CURSOR_INPUT_FILE
        with open(path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing to cursor input: {e}")
        return False

def read_from_cursor_output(target_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Read and parse response from cursor output file."""
    try:
        path = target_path or config.CURSOR_OUTPUT_FILE
        if not os.path.exists(path):
            return None
            
        with open(path, 'r') as f:
            content = f.read()
            
        if not content:
            return None
            
        return json.loads(content)
    except Exception as e:
        print(f"Error reading cursor output: {e}")
        return None

async def stage_and_execute_prompt(template_name: str, context: Dict[str, Any], timeout_seconds: int = 30) -> Optional[Dict[str, Any]]:
    """Stage a prompt and wait for cursor response."""
    if not stage_prompt_for_cursor(template_name, context):
        return None
        
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout_seconds:
        response = read_from_cursor_output()
        if response is not None:
            return response
        time.sleep(1)
        
    print("Timeout waiting for cursor response")
    return None 