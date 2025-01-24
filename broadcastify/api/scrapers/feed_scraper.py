"""
Scraper for Broadcastify feed information.
"""

import re
import logging
from typing import Dict, List, Optional, Union
from bs4 import BeautifulSoup, Tag
import requests

from ..models import Feed, MetroFeed
from ..utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class FeedScraper:
    """
    Scraper for Broadcastify feed information.
    
    This handles scraping from multiple URL patterns:
    - /listen/stid/{state_id}  (state feeds)
    - /listen/ctid/{county_id} (county feeds)
    - /listen/mid/{metro_id}   (metro area feeds)
    - /listen/feed/{feed_id}   (individual feed)
    """
    
    def __init__(self, client):
        self.client = client
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        })
        self.headers = self.session.headers
    
    def _get_state_id(self, state: Union[int, str]) -> Optional[int]:
        """Get state ID from name or ID."""
        if isinstance(state, int):
            return state
            
        # Map of state names to IDs - from website's select list
        state_ids = {
            'alabama': 1,
            'alaska': 2,
            'arizona': 4,
            'arkansas': 5,
            'california': 6,
            'colorado': 8,
            'connecticut': 9,
            'delaware': 10,
            'district of columbia': 11,
            'florida': 12,
            'georgia': 13,
            'guam': 66,
            'hawaii': 15,
            'idaho': 16,
            'illinois': 17,
            'indiana': 18,
            'iowa': 19,
            'kansas': 20,
            'kentucky': 21,
            'louisiana': 22,
            'maine': 23,
            'maryland': 24,
            'massachusetts': 25,
            'michigan': 26,
            'minnesota': 27,
            'mississippi': 28,
            'missouri': 29,
            'montana': 30,
            'nebraska': 31,
            'nevada': 32,
            'new hampshire': 33,
            'new jersey': 34,
            'new mexico': 35,
            'new york': 36,
            'north carolina': 37,
            'north dakota': 38,
            'ohio': 39,
            'oklahoma': 40,
            'oregon': 41,
            'pennsylvania': 42,
            'puerto rico': 72,
            'rhode island': 44,
            'south carolina': 45,
            'south dakota': 46,
            'tennessee': 47,
            'texas': 48,
            'utah': 49,
            'vermont': 50,
            'virgin islands': 78,
            'virginia': 51,
            'washington': 53,
            'west virginia': 54,
            'wisconsin': 55,
            'wyoming': 56
        }
        
        state_name = state.lower().strip()
        return state_ids.get(state_name)

    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        """Make a request to the Broadcastify website."""
        try:
            # Wait for rate limit
            self.rate_limiter.wait()
            
            response = requests.get(
                url,
                cookies=self.session.cookies,
                headers=self.headers
            )
            response.raise_for_status()
            
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _parse_feed_row(self, row: Tag, metro_id: Optional[int] = None) -> Optional[Feed]:
        """Parse a feed row from the table."""
        try:
            cells = row.find_all(['td', 'th'])
            if not cells or len(cells) < 5:
                return None
                
            # Skip header rows
            if row.find('th'):
                return None
                
            # Get feed ID from the cell's ID attribute
            feed_id_match = re.search(r'l-(\d+)', cells[0].get('id', ''))
            if not feed_id_match:
                return None
            feed_id = int(feed_id_match.group(1))
            
            # Get feed name and description from the second cell
            name_link = cells[1].find('a')
            if not name_link:
                return None
            name = name_link.text.strip()
            
            # Description is in a rrfont span if present
            desc_span = cells[1].find('span', {'class': 'rrfont'})
            description = desc_span.text.strip() if desc_span else ''
            
            # Get location from the third cell
            location = cells[2].text.strip()
            
            # Get listeners from the fourth cell
            try:
                listeners = int(cells[3].text.strip())
            except (ValueError, IndexError):
                listeners = 0
                
            # Get status from the last cell
            status = cells[-1].text.strip()
            
            # Create appropriate feed type based on whether this is a metro feed
            if metro_id is not None:
                return MetroFeed(
                    id=feed_id,
                    name=name,
                    description=description,
                    location=location,
                    status=status,
                    listeners=listeners,
                    metro_area_id=metro_id
                )
            else:
                return Feed(
                    id=feed_id,
                    name=name,
                    description=description,
                    location=location,
                    status=status,
                    listeners=listeners
                )
                
        except Exception as e:
            logger.error(f"Error parsing feed row: {e}")
            return None
    
    def get_feeds_by_state(self, state: str) -> List[Feed]:
        """Get all feeds for a state."""
        state_id = self._get_state_id(state)
        if not state_id:
            logger.error(f"Could not find state ID for {state}")
            return []
            
        url = f"https://www.broadcastify.com/listen/stid/{state_id}"
        logger.debug(f"Fetching state page from {url}")
        
        soup = self._make_request(url)
        if not soup:
            return []
            
        # Use a set to deduplicate feeds by ID
        feeds_by_id = {}
        
        # First get county IDs from the county select box
        county_select = soup.find('select', {'name': 'ctid'})
        if county_select:
            for option in county_select.find_all('option'):
                try:
                    # County options have format "ctid,ID"
                    county_value = option['value']
                    if ',' in county_value:
                        _, county_id = county_value.split(',')
                        county_id = int(county_id)
                        county_name = option.text.strip()
                        logger.debug(f"Processing county {county_name} (ID: {county_id})")
                        county_feeds = self.get_feeds_by_county(county_id)
                        for feed in county_feeds:
                            feeds_by_id[feed.id] = feed
                except (ValueError, KeyError) as e:
                    logger.error(f"Error processing county option: {e}")
                    continue
        else:
            logger.error("Could not find county select box")
            
        # Then get metro area IDs from the metro select box
        metro_select = soup.find('select', {'name': 'mid', 'class': 'navBox'})
        if metro_select:
            for option in metro_select.find_all('option'):
                try:
                    # Metro options have format "mid,ID"
                    metro_value = option['value']
                    if ',' in metro_value:
                        _, metro_id = metro_value.split(',')
                        metro_id = int(metro_id)
                        metro_name = option.text.strip()
                        logger.debug(f"Processing metro area {metro_name} (ID: {metro_id})")
                        metro_feeds = self.get_feeds_by_metro(metro_id)
                        for feed in metro_feeds:
                            # Only add metro feeds if they're not already in the list
                            # or if the existing feed isn't a metro feed
                            if feed.id not in feeds_by_id or not isinstance(feeds_by_id[feed.id], MetroFeed):
                                feeds_by_id[feed.id] = feed
                except (ValueError, KeyError) as e:
                    logger.error(f"Error processing metro option: {e}")
                    continue
        else:
            logger.error("Could not find metro select box")
            
        return list(feeds_by_id.values())
        
    def get_feeds_by_metro(self, metro_id: int) -> List[Feed]:
        """Get all feeds for a metro area."""
        url = f"https://www.broadcastify.com/listen/mid/{metro_id}"
        logger.debug(f"Fetching metro page from {url}")
        
        soup = self._make_request(url)
        if not soup:
            return []
            
        feeds = []
        
        # Find all feed rows in the main table
        feed_table = soup.find('table', {'class': 'btable'})
        if not feed_table:
            logger.error(f"Could not find feed table on metro page {metro_id}")
            return []
            
        rows = feed_table.find_all('tr')
        logger.debug(f"Found {len(rows)} rows in feed table")
        
        # Skip the first row (header)
        for row in rows[1:]:
            feed = self._parse_feed_row(row, metro_id=metro_id)
            if feed:
                feeds.append(feed)
        
        logger.debug(f"Found {len(feeds)} feeds in metro area {metro_id}")
        return feeds
    
    def get_feeds_by_county(self, county_id: int) -> List[Feed]:
        """Get all feeds for a county."""
        url = f"https://www.broadcastify.com/listen/ctid/{county_id}"
        logger.debug(f"Fetching county page from {url}")
        
        soup = self._make_request(url)
        if not soup:
            return []
            
        feeds = []
        
        # Find all feed rows in the main table
        feed_table = soup.find('table', {'class': 'btable'})
        if not feed_table:
            logger.error(f"Could not find feed table on county page {county_id}")
            return []
            
        rows = feed_table.find_all('tr')
        logger.debug(f"Found {len(rows)} rows in feed table")
        
        # Skip the first row (header)
        for row in rows[1:]:
            feed = self._parse_feed_row(row)
            if feed:
                feeds.append(feed)
        
        logger.debug(f"Found {len(feeds)} feeds in county {county_id}")
        
        # Only check coverage if there are talkgroups
        coverage_form = soup.find('form', {'action': '/calls/coverage/ctid/'})
        if coverage_form and soup.find('div', {'class': 'talkgroup'}):
            # Get the county ID from the hidden input
            ctid_input = coverage_form.find('input', {'name': 'ctid'})
            if ctid_input:
                ctid = ctid_input.get('value')
                # Get all service types from the select options
                service_select = coverage_form.find('select', {'name': 'tagId'})
                if service_select:
                    for option in service_select.find_all('option'):
                        tag_id = option.get('value')
                        if tag_id:
                            coverage_url = f"https://www.broadcastify.com/calls/coverage/ctid/?tagId={tag_id}&ctid={ctid}"
                            logger.debug(f"Found coverage form, checking URL: {coverage_url}")
                            coverage_feeds = self.get_feeds_from_coverage(coverage_url)
                            logger.debug(f"Found {len(coverage_feeds)} feeds from coverage with tagId={tag_id}")
                            feeds.extend(coverage_feeds)
        
        return feeds
    
    def get_feeds_from_coverage(self, coverage_url: str) -> List[Feed]:
        """Get feeds from a coverage page."""
        logger.debug(f"Checking coverage page: {coverage_url}")
        
        soup = self._make_request(coverage_url)
        if not soup:
            return []
            
        feeds = []
        # Look for talkgroup links which contain feed information
        content_div = soup.find('div', {'class': 'content'})
        if not content_div:
            return []
            
        for link in content_div.find_all('a'):
            href = link.get('href', '')
            if '/calls/tg/' in href:
                match = re.search(r'/tg/(\d+)/(\d+)', href)
                if match:
                    system_id = int(match.group(1))
                    talkgroup_id = int(match.group(2))
                    # Create a feed object from the talkgroup info
                    feed = Feed(
                        id=talkgroup_id,  # Use talkgroup ID as feed ID
                        name=link.text.strip(),
                        description=f"Talkgroup {talkgroup_id} in System {system_id}",
                        location="",  # County name could be added here
                        status="Unknown",
                        listeners=0
                    )
                    feeds.append(feed)
        
        return feeds
    
    def get_feed(self, feed_id: int) -> Optional[Feed]:
        """Get detailed information about a specific feed."""
        url = f"https://www.broadcastify.com/listen/feed/{feed_id}"
        soup = self._make_request(url)
        if not soup:
            return None
            
        try:
            # Extract feed details from the page
            title = soup.find('h1', {'class': 'btitle'})
            description = soup.find('div', {'class': 'bdescription'})
            status_div = soup.find('div', {'class': 'bstatus'})
            
            return Feed(
                id=feed_id,
                name=title.text.strip() if title else "Unknown",
                description=description.text.strip() if description else "",
                location="",  # Need to parse location from page
                status=status_div.text.strip() if status_div else "Unknown"
            )
        except Exception as e:
            logger.error(f"Error parsing feed {feed_id}: {e}")
            return None
