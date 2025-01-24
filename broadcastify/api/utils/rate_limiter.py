"""
Rate limiting functionality to avoid overloading the Broadcastify servers.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional

class RateLimiter:
    """
    Rate limiter to prevent excessive requests to Broadcastify.
    
    This implements a token bucket algorithm with different rate limits
    for different types of requests.
    """
    
    def __init__(self):
        self.last_request: Dict[str, datetime] = {}
        self.limits = {
            "default": timedelta(seconds=1),  # 1 request per second
            "live": timedelta(seconds=5),     # 1 request per 5 seconds for live calls
            "archive": timedelta(seconds=2),   # 1 request per 2 seconds for archives
            "scrape": timedelta(seconds=3),    # 1 request per 3 seconds for scraping
        }
    
    def wait(self, request_type: str = "default") -> None:
        """
        Wait until it's safe to make another request.
        
        Args:
            request_type: Type of request being made. Controls which rate limit is used.
        """
        if request_type in self.last_request:
            elapsed = datetime.now() - self.last_request[request_type]
            limit = self.limits.get(request_type, self.limits["default"])
            if elapsed < limit:
                time.sleep((limit - elapsed).total_seconds())
        
        self.last_request[request_type] = datetime.now()
        
    def __enter__(self, request_type: str = "default"):
        """Enter context manager."""
        self.wait(request_type)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        pass
