"""
Scraper for Broadcastify call information.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests

from ..models import Call
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class CallScraper:
    """
    Scraper for Broadcastify call information.
    
    This handles scraping from multiple URL patterns:
    - /calls/tg/{system_id}/{talkgroup_id} (live calls for a talkgroup)
    - /calls/trs/{system_id} (system talkgroups)
    - /calls/coverage/ctid/?tagId={tag}&ctid={county} (county coverage)
    """
    
    def __init__(self, client):
        self.client = client
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        })
    
    def _make_request(self, url: str, method: str = "GET", data: Dict = None) -> Optional[dict]:
        """Make a rate-limited request and return JSON response."""
        self.rate_limiter.wait("live" if "live" in url else "archive")
        try:
            if method == "GET":
                response = self.session.get(url)
            else:
                response = self.session.post(url, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def get_live_calls(self, system_id: int, talkgroup_id: int) -> List[Call]:
        """
        Get live calls for a talkgroup.
        
        Args:
            system_id: System ID
            talkgroup_id: Talkgroup ID
            
        Returns:
            List of Call objects
        """
        url = f"https://www.broadcastify.com/calls/tg/{system_id}/{talkgroup_id}"
        
        # First, load the talkgroup page to get any necessary tokens
        self.session.get(url)
        
        # Now make the AJAX request for live calls
        data = {
            "action": "get_calls",
            "system": system_id,
            "talkgroup": talkgroup_id,
            "time": datetime.now().timestamp()
        }
        
        response = self._make_request(
            f"https://www.broadcastify.com/calls/ajax/",
            method="POST",
            data=data
        )
        
        if not response or "calls" not in response:
            return []
            
        calls = []
        for call_data in response["calls"]:
            try:
                call = Call(
                    id=call_data["id"],
                    system_id=system_id,
                    talkgroup_id=talkgroup_id,
                    start_time=datetime.fromtimestamp(float(call_data["start"])),
                    duration=float(call_data["dur"]),
                    audio_url=call_data.get("audio"),
                    source="live"
                )
                calls.append(call)
            except Exception as e:
                logger.error(f"Error parsing call data: {e}")
                continue
                
        return calls
    
    def get_archived_calls(
        self,
        system_id: int,
        talkgroup_id: int,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Call]:
        """Get archived calls for a talkgroup within a time range."""
        # Implementation similar to get_live_calls but for archived calls
        pass
    
    def get_county_coverage(self, county_id: int, tag_id: int = 1) -> Dict:
        """
        Get coverage information for a county.
        
        Args:
            county_id: County ID
            tag_id: Tag ID (1 for law enforcement, 2 for fire/EMS, etc.)
            
        Returns:
            Dictionary of coverage information
        """
        url = f"https://www.broadcastify.com/calls/coverage/ctid/?tagId={tag_id}&ctid={county_id}"
        return self._make_request(url) or {}
