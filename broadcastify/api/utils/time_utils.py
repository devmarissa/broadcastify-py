"""
Time-related utility functions.
"""

from datetime import datetime, timedelta

def floor_dt(dt: datetime, delta: timedelta) -> datetime:
    """
    Floor a datetime to the nearest multiple of delta.
    
    Args:
        dt: Datetime to floor
        delta: Time interval to floor to
        
    Returns:
        Floored datetime
    """
    return dt - (dt - datetime.min) % delta

def floor_dt_s(timestamp: float, interval: int = 1800) -> float:
    """
    Floor a UNIX timestamp to the nearest interval.
    
    Args:
        timestamp: UNIX timestamp to floor
        interval: Interval in seconds (default: 1800 = 30 minutes)
        
    Returns:
        Floored UNIX timestamp
    """
    return timestamp - (timestamp % interval)
