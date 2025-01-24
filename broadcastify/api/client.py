"""
Main client interface for interacting with Broadcastify services.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import requests

from .models import Call, Feed, System, Talkgroup
from .scrapers import CallScraper, FeedScraper, SystemScraper
from .utils import RateLimiter, Cache

logger = logging.getLogger(__name__)

class BroadcastifyClient:
    """
    High-level client for interacting with Broadcastify services.
    
    This client provides access to both the live audio feeds and the calls platform.
    It handles authentication, rate limiting, and caching automatically.
    """
    
    def __init__(self, username: str, password: str, cache_dir: str = ".bc_cache"):
        self.username = username
        self.password = password
        self.cache = Cache(cache_dir)
        self.rate_limiter = RateLimiter()
        
        # Initialize session
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
        
        # Initialize scrapers with this client instance
        self.call_scraper = CallScraper(self)
        self.feed_scraper = FeedScraper(self)
        self.system_scraper = SystemScraper(self)
        
        self._credential_key = None
    
    def login(self) -> bool:
        """
        Authenticate with Broadcastify.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # First, get the login page to get any necessary tokens
            response = self._session.get("https://www.broadcastify.com/login")
            response.raise_for_status()
            
            # Make login request
            data = {
                "username": self.username,
                "password": self.password,
                "action": "auth",
                "redirect": "/"
            }
            
            response = self._session.post(
                "https://www.broadcastify.com/login",
                data=data,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Check if login was successful by looking for success indicators
            if "Login - Broadcastify" not in response.text:
                logger.info("Login successful")
                return True
            else:
                logger.error("Login failed - incorrect credentials or invalid response")
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def get_system(self, system_id: Union[int, str]) -> Optional[System]:
        """Get information about a radio system."""
        # Implementation here
        pass
    
    def get_talkgroups(self, system_id: Union[int, str]) -> List[Talkgroup]:
        """Get all talkgroups for a system."""
        # Implementation here
        pass
    
    def get_live_calls(self, system_id: Union[int, str], talkgroup_id: int) -> List[Call]:
        """Get recent calls for a talkgroup."""
        # Implementation here
        pass
    
    def get_archived_calls(
        self, 
        system_id: Union[int, str], 
        talkgroup_id: int,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Call]:
        """Get archived calls for a talkgroup within a time range."""
        # Implementation here
        pass
    
    def get_feed(self, feed_id: int) -> Optional[Feed]:
        """Get information about a live audio feed."""
        # Implementation here
        pass
    
    def get_feeds_by_state(self, state: Union[int, str]) -> List[Feed]:
        """Get all feeds for a state (can use state name or ID)."""
        # Implementation here
        pass
