"""Time-related utility functions for the HCshinobi bot."""

from datetime import timedelta

def format_time_delta(delta: timedelta) -> str:
    """Format a timedelta into a human-readable string."""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)

def pretty_print_duration(seconds: int) -> str:
    """Format seconds into a human-readable duration string."""
    return format_time_delta(timedelta(seconds=seconds)) 