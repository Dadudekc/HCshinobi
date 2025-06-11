from typing import List, Optional, Any
from unittest.mock import AsyncMock, MagicMock
import discord

class InteractionTrace:
    """Utility class to track and verify Discord interaction lifecycles."""
    
    def __init__(self):
        self.defer_calls: List[dict] = []
        self.send_calls: List[dict] = []
        self.followup_send_calls: List[dict] = []
        self.edit_calls: List[dict] = []
        self.delete_calls: List[dict] = []
        
    def create_mock_ctx(self) -> MagicMock:
        """Create a mock context with traced interaction methods."""
        ctx = MagicMock()
        
        # Create response mock
        ctx.response = AsyncMock()
        ctx.response.defer = AsyncMock(side_effect=self._trace_defer)
        
        # Create followup mock
        ctx.followup = AsyncMock()
        ctx.followup.send = AsyncMock(side_effect=self._trace_followup_send)
        
        # Create message mock
        ctx.message = AsyncMock()
        ctx.message.edit = AsyncMock(side_effect=self._trace_edit)
        ctx.message.delete = AsyncMock(side_effect=self._trace_delete)
        
        return ctx
    
    async def _trace_defer(self, **kwargs):
        """Trace a defer call."""
        self.defer_calls.append(kwargs)
        return None
    
    async def _trace_followup_send(self, **kwargs):
        """Trace a followup send call."""
        self.followup_send_calls.append(kwargs)
        return None
    
    async def _trace_edit(self, **kwargs):
        """Trace an edit call."""
        self.edit_calls.append(kwargs)
        return None
    
    async def _trace_delete(self, **kwargs):
        """Trace a delete call."""
        self.delete_calls.append(kwargs)
        return None
    
    def assert_defer_called(self, **kwargs) -> None:
        """Assert that defer was called with the given parameters."""
        assert any(self._match_call(call, kwargs) for call in self.defer_calls), \
            f"Expected defer call with {kwargs}, got {self.defer_calls}"
    
    def assert_followup_send_called(self, **kwargs) -> None:
        """Assert that followup.send was called with the given parameters."""
        assert any(self._match_call(call, kwargs) for call in self.followup_send_calls), \
            f"Expected followup.send call with {kwargs}, got {self.followup_send_calls}"
    
    def assert_edit_called(self, **kwargs) -> None:
        """Assert that edit was called with the given parameters."""
        assert any(self._match_call(call, kwargs) for call in self.edit_calls), \
            f"Expected edit call with {kwargs}, got {self.edit_calls}"
    
    def assert_delete_called(self, **kwargs) -> None:
        """Assert that delete was called with the given parameters."""
        assert any(self._match_call(call, kwargs) for call in self.delete_calls), \
            f"Expected delete call with {kwargs}, got {self.delete_calls}"
    
    def _match_call(self, call: dict, expected: dict) -> bool:
        """Match a call against expected parameters."""
        return all(call.get(k) == v for k, v in expected.items())
    
    def assert_interaction_sequence(self, *expected_calls: dict) -> None:
        """Assert that interactions happened in the expected sequence."""
        all_calls = (
            [("defer", call) for call in self.defer_calls] +
            [("followup_send", call) for call in self.followup_send_calls] +
            [("edit", call) for call in self.edit_calls] +
            [("delete", call) for call in self.delete_calls]
        )
        
        for i, (call_type, expected) in enumerate(expected_calls):
            assert i < len(all_calls), f"Expected {len(expected_calls)} calls, got {len(all_calls)}"
            actual_type, actual = all_calls[i]
            assert actual_type == call_type, f"Expected {call_type}, got {actual_type}"
            assert self._match_call(actual, expected), \
                f"Expected {expected}, got {actual}" 