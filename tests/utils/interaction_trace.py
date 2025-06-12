"""
Utility class for tracing Discord interactions in tests.
"""
from typing import Optional, List, Dict, Any, Union, Pattern
import re
import discord
from discord import app_commands
from unittest.mock import AsyncMock, MagicMock

class InteractionTrace:
    """Tracks the history of interactions and responses for testing."""
    
    def __init__(self):
        self.responses: List[Dict[str, Any]] = []
        self.deferred = False
        self.ephemeral = False
        self.thinking = False
        self.defer_calls = []
        self.response_send_calls = []
        self.followup_send_calls = []
        
    async def defer(self, ephemeral: bool = False, thinking: bool = True):
        """Simulate deferring a response."""
        self.deferred = True
        self.ephemeral = ephemeral
        self.thinking = thinking
        self.defer_calls.append(MagicMock(kwargs={'ephemeral': ephemeral, 'thinking': thinking}))
        return None
        
    async def response(self, content: Optional[str] = None, **kwargs):
        """Record a response."""
        response_data = {
            "content": content,
            **kwargs
        }
        self.responses.append(response_data)
        self.response_send_calls.append(MagicMock(kwargs=response_data))
        return None
        
    async def followup(self, content: Optional[str] = None, **kwargs):
        """Record a followup message."""
        followup_data = {
            "content": content,
            **kwargs
        }
        self.responses.append(followup_data)
        self.followup_send_calls.append(MagicMock(kwargs=followup_data))
        return None
        
    def get_last_response(self) -> Optional[Dict[str, Any]]:
        """Get the last response if any."""
        return self.responses[-1] if self.responses else None
        
    def clear(self):
        """Clear all recorded responses."""
        self.responses.clear()
        self.deferred = False
        self.ephemeral = False
        self.thinking = False
        self.defer_calls.clear()
        self.response_send_calls.clear()
        self.followup_send_calls.clear()

    def create_mock_ctx(self):
        """Create a mock Discord interaction context."""
        mock_ctx = AsyncMock()
        
        # Set up user
        mock_user = AsyncMock()
        mock_user.id = 123456789
        mock_user.name = "TestUser"
        mock_user.display_name = "Test User"
        mock_ctx.user = mock_user
        
        # Set up guild and permissions
        mock_ctx.guild = AsyncMock()
        mock_ctx.guild_permissions = AsyncMock()
        mock_ctx.guild_permissions.administrator = True
        
        # Set up response methods with explicit returns
        mock_ctx.defer = AsyncMock(return_value=None)
        mock_ctx.response = AsyncMock()
        mock_ctx.response.send_message = AsyncMock(return_value=None)
        mock_ctx.followup = AsyncMock()
        mock_ctx.followup.send = AsyncMock(return_value=None)
        
        # Set up interaction with user
        mock_ctx.interaction = AsyncMock()
        mock_ctx.interaction.user = mock_user  # Use the same mock user
        mock_ctx.interaction.guild = mock_ctx.guild
        mock_ctx.interaction.response = mock_ctx.response
        mock_ctx.interaction.followup = mock_ctx.followup
        
        # Set up defer method to record calls
        async def defer_wrapper(*args, **kwargs):
            self.defer_calls.append(MagicMock(kwargs=kwargs))
            self.deferred = True
            self.ephemeral = kwargs.get('ephemeral', False)
            self.thinking = kwargs.get('thinking', True)
            return None
            
        mock_ctx.interaction.response.defer = defer_wrapper

        # Set up followup send method to record calls
        async def followup_send_wrapper(*args, **kwargs):
            if args and isinstance(args[0], str):
                kwargs['content'] = args[0]
            self.followup_send_calls.append(MagicMock(kwargs=kwargs))
            return None
            
        mock_ctx.interaction.followup.send = followup_send_wrapper
        mock_ctx.followup.send = followup_send_wrapper
        
        return mock_ctx

    def _match_content(self, expected: Union[str, Pattern], actual: Optional[str]) -> bool:
        """Match content using exact string, substring, or regex pattern.
        
        Args:
            expected: Expected content (string or regex pattern)
            actual: Actual content to check
            
        Returns:
            bool: True if content matches, False otherwise
        """
        if actual is None:
            return expected is None
            
        if isinstance(expected, Pattern):
            return bool(expected.search(actual))
        elif isinstance(expected, str):
            return expected in actual
        return expected == actual

    def _match_embed(self, expected: Any, actual: Any) -> bool:
        """Match embed using type or instance check.
        
        Args:
            expected: Expected embed type or instance
            actual: Actual embed to check
            
        Returns:
            bool: True if embed matches, False otherwise
        """
        if isinstance(expected, type) and issubclass(expected, discord.Embed):
            return isinstance(actual, discord.Embed)
        return expected == actual

    def assert_interaction_sequence(self, *expected_sequence):
        """Assert that the interaction sequence matches the expected sequence.
        
        Args:
            *expected_sequence: Tuple of (action, kwargs) pairs that should match the sequence
                              of interactions that occurred.
        """
        actual_sequence = []
        
        # Record defer calls
        for call in self.defer_calls:
            actual_sequence.append(("defer", call.kwargs))
            
        # Record response_send calls
        for call in self.response_send_calls:
            actual_sequence.append(("response_send", call.kwargs))
            
        # Record followup_send calls
        for call in self.followup_send_calls:
            actual_sequence.append(("followup_send", call.kwargs))
            
        # Compare sequences
        assert len(actual_sequence) == len(expected_sequence), \
            f"Expected {len(expected_sequence)} interactions but got {len(actual_sequence)}"
            
        for actual, expected in zip(actual_sequence, expected_sequence):
            assert actual[0] == expected[0], \
                f"Expected action {expected[0]} but got {actual[0]}"
            
            # For defer calls, handle thinking parameter specially
            if actual[0] == "defer":
                actual_kwargs = actual[1].copy()
                expected_kwargs = expected[1].copy()
                
                # If thinking is not specified in expected, remove it from actual
                if 'thinking' not in expected_kwargs:
                    actual_kwargs.pop('thinking', None)
                
                assert actual_kwargs == expected_kwargs, \
                    f"Expected kwargs {expected_kwargs} but got {actual_kwargs} for action {actual[0]}"
            else:
                # For followup_send calls, handle special cases
                if actual[0] == "followup_send":
                    actual_kwargs = actual[1].copy()
                    expected_kwargs = expected[1].copy()
                    
                    # Remove is_followup if not in expected kwargs
                    if 'is_followup' not in expected_kwargs:
                        actual_kwargs.pop('is_followup', None)
                    
                    # Handle embed comparison
                    if 'embed' in expected_kwargs and 'embed' in actual_kwargs:
                        expected_embed = expected_kwargs.pop('embed')
                        actual_embed = actual_kwargs.pop('embed')
                        assert self._match_embed(expected_embed, actual_embed), \
                            f"Expected embed {expected_embed} but got {actual_embed}"
                    
                    # Remove ephemeral if not in expected kwargs
                    if 'ephemeral' not in expected_kwargs:
                        actual_kwargs.pop('ephemeral', None)
                    
                    # Handle content comparison
                    if 'content' in expected_kwargs and 'content' in actual_kwargs:
                        expected_content = expected_kwargs.pop('content')
                        actual_content = actual_kwargs.pop('content')
                        assert self._match_content(expected_content, actual_content), \
                            f"Expected content {expected_content} but got {actual_content}"
                    
                    assert actual_kwargs == expected_kwargs, \
                        f"Expected kwargs {expected_kwargs} but got {actual_kwargs} for action {actual[0]}"
                else:
                    assert actual[1] == expected[1], \
                        f"Expected kwargs {expected[1]} but got {actual[1]} for action {actual[0]}"

    def assert_defer_called(self, ephemeral=True, thinking=True):
        """Assert that defer was called with the expected parameters.
        
        Args:
            ephemeral (bool): Whether the response should be ephemeral
            thinking (bool): Whether the thinking state should be set
        """
        assert len(self.defer_calls) > 0, "Expected defer to be called but it wasn't"
        
        last_defer = self.defer_calls[-1]
        assert last_defer.kwargs.get('ephemeral') == ephemeral, \
            f"Expected ephemeral={ephemeral} but got {last_defer.kwargs.get('ephemeral')}"
            
        assert self.thinking == thinking, \
            f"Expected thinking={thinking} but got {self.thinking}"

    def assert_followup_send_called(self, content=None, **kwargs):
        """Assert that followup.send was called with the expected parameters.
        
        Args:
            content (str, optional): Expected content of the followup message
            **kwargs: Additional expected keyword arguments
        """
        assert len(self.followup_send_calls) > 0, "Expected followup.send to be called but it wasn't"
        
        last_followup = self.followup_send_calls[-1]
        actual_kwargs = last_followup.kwargs.copy()
        
        # Remove is_followup if not in expected kwargs
        if 'is_followup' not in kwargs:
            actual_kwargs.pop('is_followup', None)
            
        # Remove ephemeral if not in expected kwargs
        if 'ephemeral' not in kwargs:
            actual_kwargs.pop('ephemeral', None)
            
        if content is not None:
            assert self._match_content(content, actual_kwargs.get('content')), \
                f"Expected content={content} but got {actual_kwargs.get('content')}"
                
        for key, value in kwargs.items():
            # Handle embed comparison
            if key == 'embed':
                assert self._match_embed(value, actual_kwargs.get(key)), \
                    f"Expected {key}={value} but got {actual_kwargs.get(key)}"
            else:
                assert actual_kwargs.get(key) == value, \
                    f"Expected {key}={value} but got {actual_kwargs.get(key)}" 