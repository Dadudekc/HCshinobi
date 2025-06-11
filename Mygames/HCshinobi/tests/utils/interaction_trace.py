from typing import List, Dict, Any, Optional, Union
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
import discord

class InteractionTrace:
    """Tracks Discord interaction calls for testing."""
    
    def __init__(self):
        self.defer_calls: List[SimpleNamespace] = []
        self.response_send_calls: List[SimpleNamespace] = []
        self.followup_send_calls: List[SimpleNamespace] = []
        self.edit_calls: List[SimpleNamespace] = []
        self.delete_calls: List[SimpleNamespace] = []

    def create_mock_ctx(self):
        """Create a mock context with interaction tracking."""
        mock_ctx = AsyncMock()
        
        # Add user attribute
        mock_ctx.user = AsyncMock()
        mock_ctx.user.id = 123456789
        
        # Add response attribute
        mock_ctx.response = AsyncMock()
        mock_ctx.response.defer = AsyncMock()
        mock_ctx.response.send_message = AsyncMock()
        mock_ctx.response.is_done = AsyncMock(return_value=False)
        
        # Add followup attribute
        mock_ctx.followup = AsyncMock()
        mock_ctx.followup.send = AsyncMock()
        
        # Track interactions
        self._track_interactions(mock_ctx)
        
        return mock_ctx

    def _track_interactions(self, mock_ctx):
        """Set up tracking of interactions for the mock context."""
        # Track defer calls
        mock_ctx.response.defer.side_effect = lambda *args, **kwargs: self._trace_defer(**kwargs)
        
        # Track response.send calls
        mock_ctx.response.send_message.side_effect = lambda *args, **kwargs: self._trace_response_send(**kwargs)
        
        # Track followup.send calls
        mock_ctx.followup.send.side_effect = lambda *args, **kwargs: self._trace_followup_send(**kwargs)

    def _trace_defer(self, **kwargs) -> None:
        """Trace a defer call."""
        self.defer_calls.append(SimpleNamespace(**kwargs))

    def _trace_response_send(self, **kwargs) -> None:
        """Trace a response.send call."""
        self.response_send_calls.append(SimpleNamespace(**kwargs))

    def _trace_followup_send(self, **kwargs) -> None:
        """Trace a followup.send call."""
        self.followup_send_calls.append(SimpleNamespace(**kwargs))

    def _trace_edit(self, **kwargs) -> None:
        """Trace an edit call."""
        self.edit_calls.append(SimpleNamespace(**kwargs))

    def _trace_delete(self, **kwargs) -> None:
        """Trace a delete call."""
        self.delete_calls.append(SimpleNamespace(**kwargs))

    def _match_call(self, call: SimpleNamespace, expected: Dict[str, Any]) -> bool:
        """Match a call against expected parameters."""
        for key, value in expected.items():
            # Handle class type checks
            if isinstance(value, type):
                if not isinstance(getattr(call, key, None), value):
                    return False
            # Handle direct value comparison
            elif getattr(call, key, None) != value:
                return False
        return True

    def assert_defer_called(self, **kwargs) -> None:
        """Assert that defer was called with the given parameters."""
        assert any(self._match_call(call, kwargs) for call in self.defer_calls), \
            f"Expected defer call with {kwargs}, got {self.defer_calls}"

    def assert_response_send_called(self, **kwargs) -> None:
        """Assert that response.send was called with the given parameters."""
        assert any(self._match_call(call, kwargs) for call in self.response_send_calls), \
            f"Expected response.send call with {kwargs}, got {self.response_send_calls}"

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

    def assert_interaction_sequence(self, *expected_calls: dict) -> None:
        """Assert that interactions happened in the expected sequence."""
        all_calls = (
            [("defer", call) for call in self.defer_calls] +
            [("response_send", call) for call in self.response_send_calls] +
            [("followup_send", call) for call in self.followup_send_calls] +
            [("edit", call) for call in self.edit_calls] +
            [("delete", call) for call in self.delete_calls]
        )

        for i, expected in enumerate(expected_calls):
            assert i < len(all_calls), f"Expected {len(expected_calls)} calls, got {len(all_calls)}"

            actual_type, actual = all_calls[i]

            # Handle both tuple and dict formats
            if isinstance(expected, tuple):
                expected_type, expected_params = expected
                assert actual_type == expected_type, f"Expected {expected_type}, got {actual_type}"
                assert self._match_call(actual, expected_params), \
                    f"Expected {expected_params}, got {actual}"
            else:
                assert self._match_call(actual, expected), \
                    f"Expected {expected}, got {actual}" 