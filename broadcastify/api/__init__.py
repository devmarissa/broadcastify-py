"""
Broadcastify API Client

This package provides a Python interface to interact with Broadcastify's web services.
It includes functionality for both the live audio feeds and the calls platform.
"""

from .client import BroadcastifyClient
from .models import Call, Feed, System, Talkgroup

__version__ = "0.1.0"
__all__ = ["BroadcastifyClient", "Call", "Feed", "System", "Talkgroup"]
