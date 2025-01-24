"""
Scraper for Broadcastify feed information.
"""

import re
import logging
from typing import Dict, List, Optional, Union
from bs4 import BeautifulSoup, Tag
import requests

from ..models import Feed, MetroFeed, ServiceCoverage, TalkgroupCoverage
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
    
    def __init__(self, session: requests.Session):
        """Initialize feed scraper."""
        self.session = session
        self.rate_limiter = RateLimiter()
        # Track which states we've already scraped coverage for
        self._scraped_coverage_states = set()
    
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
            
            response = self.session.get(url)
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
                        county_feeds = self.get_feeds_by_county(county_id, state_id)
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
    
    def get_feeds_by_county(self, county_id: int, state_id: int) -> List[Feed]:
        """Get feeds for a county."""
        url = f"https://www.broadcastify.com/listen/ctid/{county_id}"
        logger.debug(f"Fetching county page from {url}")
        
        soup = self._make_request(url)
        if not soup:
            return []
            
        feeds = []
        
        # First get feeds from the main table
        feed_table = soup.find('table', {'class': 'btable'})
        if feed_table:
            for row in feed_table.find_all('tr')[1:]:  # Skip header row
                feed = self._parse_feed_row(row)
                if feed:
                    feeds.append(feed)
                    
        # Check if this county has a coverage form and we haven't scraped this state yet
        if state_id not in self._scraped_coverage_states:
            logger.debug(f"Checking coverage for state {state_id}")
            coverage_form = soup.find('form', {'action': '/calls/coverage/ctid/'})
            if coverage_form:
                logger.debug("Found coverage form")
                service_select = coverage_form.find('select', {'name': 'tagId'})
                if service_select:
                    logger.debug("Found service select")
                    # Get all service types available
                    for option in service_select.find_all('option'):
                        try:
                            tag_id = int(option['value'])
                            service_name = option.text.strip()
                            logger.debug(f"Processing service: {service_name} (tagId={tag_id})")
                            
                            coverage_url = f"https://www.broadcastify.com/calls/coverage/ctid/?tagId={tag_id}&ctid={county_id}"
                            logger.debug(f"Fetching coverage from: {coverage_url}")
                            
                            coverage_services = self.get_feeds_from_coverage(coverage_url)
                            logger.debug(f"Found {len(coverage_services)} services from coverage")
                            
                            # Here you can process the coverage_services as needed
                            # For now, let's convert them to Feed objects
                            for service in coverage_services:
                                for tg in service.talkgroups:
                                    feed = Feed(
                                        id=tg.id,
                                        name=tg.display,
                                        description=tg.description,
                                        location=tg.system,
                                        status=tg.last_seen,
                                        listeners=0
                                    )
                                    feeds.append(feed)
                                    
                        except (ValueError, KeyError) as e:
                            logger.error(f"Error processing service option: {e}")
                            continue
                            
                    # Mark this state as scraped for coverage
                    self._scraped_coverage_states.add(state_id)
                    
        return feeds
    
    def get_feeds_from_coverage(self, url: str) -> List[ServiceCoverage]:
        """Get feeds from a coverage page."""
        logger.debug(f"Fetching coverage page from {url}")
        
        soup = self._make_request(url)
        if not soup:
            return []
            
        services = []
        
        # Find all service cards
        cards = soup.find_all('div', {'class': 'card-frame'})
        for card in cards:
            # Get service name from header
            header = card.find('h6', {'class': 'card-header'})
            if not header:
                continue
            service_name = header.text.strip()
            
            # Get tag ID from URL
            tag_id_match = re.search(r'tagId=(\d+)', url)
            if not tag_id_match:
                continue
            tag_id = int(tag_id_match.group(1))
            
            # Find talkgroup table
            table = card.find('table', {'class': 'groupsTable'})
            if not table:
                continue
                
            talkgroups = []
            
            # Process each row
            for row in table.find_all('tr')[1:]:  # Skip header row
                try:
                    cells = row.find_all('td')
                    if len(cells) < 5:
                        continue
                        
                    # Get talkgroup ID from first cell
                    tg_link = cells[0].find('a')
                    if not tg_link:
                        continue
                    tg_value = tg_link.get('data-value', '')
                    if not tg_value or '-' not in tg_value:
                        continue
                    system_id, tg_id = tg_value.split('-')
                    
                    talkgroups.append(TalkgroupCoverage(
                        id=int(tg_id),
                        system_id=int(system_id),
                        display=cells[1].text.strip(),
                        description=cells[2].text.strip(),
                        system=cells[3].text.strip(),
                        last_seen=cells[4].text.strip()
                    ))
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing talkgroup row: {e}")
                    continue
            
            if talkgroups:
                services.append(ServiceCoverage(
                    tag_id=tag_id,
                    name=service_name,
                    talkgroups=talkgroups
                ))
        
        return services
    
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
