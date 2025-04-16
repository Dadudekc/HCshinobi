"""Shared utilities for testing LLM-related functionality."""
from typing import Any, Dict, Optional, List
from unittest.mock import Mock, AsyncMock

class LLMTestResponse:
    """Test response formats for LLM outputs."""
    
    @staticmethod
    def with_json(content: Any) -> str:
        """Create a response with JSON content."""
        return f'''Here's the output:
```json
{content}
```
Some trailing text.'''
    
    @staticmethod
    def with_code(code: str, language: Optional[str] = None) -> str:
        """Create a response with code block."""
        lang_tag = f"{language}\n" if language else ""
        return f'''Here's some code:
```{lang_tag}{code}
```'''
    
    @staticmethod
    def with_list(items: List[str], format: str = "bullet") -> str:
        """Create a response with a list in specified format."""
        if format == "bullet":
            items_str = "\n".join(f"- {item}" for item in items)
        elif format == "numbered":
            items_str = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
        else:
            raise ValueError(f"Unsupported list format: {format}")
        return f"Here are the items:\n{items_str}"
    
    @staticmethod
    def with_error(error_type: str = "general") -> str:
        """Create various error response patterns."""
        errors = {
            "general": "I apologize, but I encountered an error processing your request.",
            "invalid_json": "```json\n{ invalid: json }\n```",
            "empty": "",
            "no_content": "I don't have any specific output to provide.",
            "malformed": "```\nUnclosed code block"
        }
        return errors.get(error_type, errors["general"])

class LLMChainMock:
    """Mock for LLM chain testing."""
    
    def __init__(self):
        """Initialize the mock chain."""
        self.render = Mock()
        self.execute = AsyncMock()
        self.history = []
    
    def setup_response(
        self,
        response: str,
        render_result: str = "Rendered Template",
        should_fail: bool = False
    ) -> None:
        """Set up the mock response pattern."""
        self.render.return_value = render_result
        if should_fail:
            self.execute.side_effect = Exception("LLM execution failed")
        else:
            self.execute.return_value = response
    
    def verify_call(
        self,
        template: str,
        variables: Dict[str, Any],
        agent_id: str,
        purpose: str
    ) -> None:
        """Verify the LLM chain was called correctly."""
        self.render.assert_called_once_with(template, variables)
        self.execute.assert_called_once_with(
            self.render.return_value,
            agent_id=agent_id,
            purpose=purpose
        )
    
    def verify_not_called(self) -> None:
        """Verify the LLM chain was not called."""
        self.render.assert_not_called()
        self.execute.assert_not_called()

def create_llm_test_chain() -> LLMChainMock:
    """Create a pre-configured LLM chain mock."""
    return LLMChainMock()

def patch_llm_chain(target_path: str):
    """Decorator to patch LLM chain dependencies."""
    def decorator(func):
        chain = create_llm_test_chain()
        patched_func = patch(f"{target_path}.render_template", chain.render)(func)
        patched_func = patch(f"{target_path}.stage_and_execute_prompt", chain.execute)(patched_func)
        return patched_func
    return decorator 