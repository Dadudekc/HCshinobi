"""
Utility functions for the HCShinobi core system.

This module provides utility functions used across the HCShinobi system,
particularly for time formatting and display.
"""

import datetime
from typing import Union, Optional
from datetime import timedelta


def format_time_delta(delta: timedelta) -> str:
    """
    Format a timedelta into a human-readable string.
    
    Args:
        delta: The timedelta to format
        
    Returns:
        A string representation of the timedelta (e.g., "2 days, 3 hours, 45 minutes")
    """
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} {'day' if days == 1 else 'days'}")
    if hours > 0:
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if minutes > 0:
        parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
    if seconds > 0 and not parts:  # Only show seconds if no larger units
        parts.append(f"{seconds} {'second' if seconds == 1 else 'seconds'}")
    
    if not parts:
        return "less than a second"
    
    return ", ".join(parts)


def pretty_print_duration(seconds: Union[int, float, datetime.timedelta]) -> str:
    """
    Format a duration (in seconds or as a timedelta) into a human-readable string.
    
    Args:
        seconds: The duration in seconds or a timedelta object
        
    Returns:
        A formatted string (e.g., "2h 30m")
    """
    if isinstance(seconds, datetime.timedelta):
        # Convert timedelta to seconds
        seconds = seconds.total_seconds()
    
    # Ensure we're working with a number
    seconds = float(seconds)
    
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{int(days)}d")
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    if seconds > 0 and not parts:  # Only include seconds if no larger units
        parts.append(f"{int(seconds)}s")
    
    if not parts:
        return "0s"
    
    return " ".join(parts)


def time_until(target_time: datetime.datetime) -> str:
    """
    Calculate and format the time until a target datetime.
    
    Args:
        target_time: The target datetime
        
    Returns:
        A formatted string representing the time until the target
    """
    now = datetime.datetime.now(target_time.tzinfo)
    if target_time < now:
        return "already past"
    
    delta = target_time - now
    return format_time_delta(delta)


def time_since(past_time: datetime.datetime) -> str:
    """
    Calculate and format the time since a past datetime.
    
    Args:
        past_time: The past datetime
        
    Returns:
        A formatted string representing the time since the past datetime
    """
    now = datetime.datetime.now(past_time.tzinfo)
    if past_time > now:
        return "in the future"
    
    delta = now - past_time
    return format_time_delta(delta) 