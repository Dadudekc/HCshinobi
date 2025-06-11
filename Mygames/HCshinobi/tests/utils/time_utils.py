# from datetime import datetime, timedelta
from datetime import datetime, timedelta, timezone


def get_past_time(minutes: int = 5) -> datetime:
    """Return a datetime object `minutes` in the past."""
    return datetime.utcnow() - timedelta(minutes=minutes)

def get_mock_now() -> datetime:
    """Return the current UTC time with timezone."""
    return datetime.now(timezone.utc)

def get_past_hours(hours: int = 1) -> datetime:
    """Return a datetime object `hours` in the past (UTC)."""
    return get_mock_now() - timedelta(hours=hours)

def get_past_seconds(seconds: int = 60) -> datetime:
    """Return a datetime object `seconds` in the past (UTC)."""
    return get_mock_now() - timedelta(seconds=seconds) 