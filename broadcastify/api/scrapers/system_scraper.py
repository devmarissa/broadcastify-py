"""
Scraper for radio system information.
"""

import logging
import re
from typing import Dict, List, Optional, Set
import requests
from bs4 import BeautifulSoup

from ..models import System, Talkgroup
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class SystemScraper:
    """
    Scraper for radio system information.
    
    This handles scraping from multiple URL patterns:
    - /calls/trs/{system_id} (system overview)
    - /calls/tg/{system_id} (talkgroups)
    """
    
    def __init__(self, client):
        self.client = client
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })
        
        # Cache of system types
        self._system_types: Dict[int, str] = {}
    
    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Make a rate-limited request and return parsed BeautifulSoup."""
        self.rate_limiter.wait("scrape")
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _parse_system_type(self, soup: BeautifulSoup) -> str:
        """Parse the system type from the page."""
        type_div = soup.find('div', string=re.compile(r'System Type:'))
        if type_div:
            match = re.search(r'System Type:\s*(\w+)', type_div.text)
            if match:
                return match.group(1)
        return "Unknown"
    
    def _parse_talkgroup_row(self, row, system_id: int) -> Optional[Talkgroup]:
        """Parse a table row into a Talkgroup object."""
        try:
            cols = row.find_all('td')
            if len(cols) < 3:
                return None
                
            # Extract talkgroup ID and details
            tg_id = int(cols[0].text.strip())
            alpha_tag = cols[1].text.strip()
            description = cols[2].text.strip()
            
            # Check for encryption indicator
            encrypted = '🔒' in row.text or '[E]' in row.text
            
            return Talkgroup(
                id=tg_id,
                system_id=system_id,
                name=alpha_tag,
                description=description,
                encrypted=encrypted
            )
        except Exception as e:
            logger.error(f"Error parsing talkgroup row: {e}")
            return None
    
    def get_system(self, system_id: int) -> Optional[System]:
        """
        Get information about a radio system.
        
        Args:
            system_id: System ID
            
        Returns:
            System object if found, None otherwise
        """
        url = f"https://www.broadcastify.com/calls/trs/{system_id}"
        soup = self._make_request(url)
        if not soup:
            return None
            
        try:
            # Extract system name and location
            title = soup.find('h1', {'class': 'btitle'})
            if not title:
                return None
                
            # Parse system type if not cached
            if system_id not in self._system_types:
                self._system_types[system_id] = self._parse_system_type(soup)
            
            # Extract location information
            location_div = soup.find('div', {'class': 'blocation'})
            location = location_div.text.strip() if location_div else "Unknown Location"
            
            return System(
                id=system_id,
                name=title.text.strip(),
                type=self._system_types[system_id],
                location=location
            )
        except Exception as e:
            logger.error(f"Error parsing system {system_id}: {e}")
            return None
    
    def get_talkgroups(self, system_id: int) -> List[Talkgroup]:
        """
        Get all talkgroups for a system.
        
        Args:
            system_id: System ID
            
        Returns:
            List of Talkgroup objects
        """
        url = f"https://www.broadcastify.com/calls/tg/{system_id}"
        soup = self._make_request(url)
        if not soup:
            return []
            
        talkgroups = []
        tg_table = soup.find('table', {'class': 'btable'})
        if not tg_table:
            return []
            
        for row in tg_table.find_all('tr')[1:]:  # Skip header row
            tg = self._parse_talkgroup_row(row, system_id)
            if tg:
                talkgroups.append(tg)
        
        return talkgroups
