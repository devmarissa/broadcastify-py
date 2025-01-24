#!/usr/bin/env python3
"""
State Scraper Script

This script scrapes all Broadcastify endpoints for a given state, including:
- All feeds in the state
- All systems referenced by those feeds
- All talkgroups in those systems
- Recent calls for active talkgroups
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from broadcastify.api.client import BroadcastifyClient
from broadcastify.api.models import Feed, System, Talkgroup, Call

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up rich console
console = Console()

class StateScraper:
    """Scrapes all Broadcastify data for a state."""
    
    def __init__(self, username: str, password: str, output_dir: str = "output"):
        self.client = BroadcastifyClient(username, password)
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Track what we've seen
        self.seen_systems: Set[int] = set()
        self.seen_talkgroups: Set[tuple] = set()  # (system_id, tg_id)
        
        # Store results
        self.feeds: List[Feed] = []
        self.systems: Dict[int, System] = {}
        self.talkgroups: Dict[int, List[Talkgroup]] = {}
        self.recent_calls: Dict[tuple, List[Call]] = {}
    
    def scrape_state(self, state: str):
        """Scrape everything for a state."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Login
            task = progress.add_task("[cyan]Logging in...", total=None)
            if not self.client.login():
                console.print("[red]Failed to login!")
                return
            progress.remove_task(task)
            
            # Get all feeds
            task = progress.add_task("[cyan]Getting feeds...", total=None)
            self.feeds = self.client.feed_scraper.get_feeds_by_state(state)
            progress.remove_task(task)
            
            # Get systems and talkgroups
            task = progress.add_task(
                f"[cyan]Processing {len(self.feeds)} feeds...",
                total=len(self.feeds)
            )
            
            for feed in self.feeds:
                # Extract system ID from feed details
                system_id = self._extract_system_id(feed)
                if not system_id or system_id in self.seen_systems:
                    progress.advance(task)
                    continue
                    
                self.seen_systems.add(system_id)
                
                # Get system info
                system = self.client.system_scraper.get_system(system_id)
                if system:
                    self.systems[system_id] = system
                    
                    # Get talkgroups
                    talkgroups = self.client.system_scraper.get_talkgroups(system_id)
                    self.talkgroups[system_id] = talkgroups
                    
                    # Get recent calls for each talkgroup
                    for tg in talkgroups:
                        key = (system_id, tg.id)
                        if key in self.seen_talkgroups:
                            continue
                        self.seen_talkgroups.add(key)
                        
                        calls = self.client.call_scraper.get_live_calls(
                            system_id, tg.id
                        )
                        if calls:
                            self.recent_calls[key] = calls
                
                progress.advance(task)
            
            progress.remove_task(task)
        
        # Save results
        self._save_results()
        
        # Display summary
        self._display_summary()
    
    def _extract_system_id(self, feed: Feed) -> Optional[int]:
        """Extract system ID from feed details."""
        try:
            # Get detailed feed info
            feed_details = self.client.get_feed(feed.id)
            if not feed_details:
                return None
                
            # Look for system ID in description or other fields
            # Common formats:
            # - "System ID: 1234"
            # - "SystemID=1234"
            # - "SID: 1234"
            import re
            patterns = [
                r'System ID:?\s*(\d+)',
                r'SystemID=(\d+)',
                r'SID:?\s*(\d+)',
                r'/trs/(\d+)',
                r'/sid/(\d+)'
            ]
            
            text = f"{feed_details.description} {feed_details.name}"
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return int(match.group(1))
            
            return None
        except Exception as e:
            logger.error(f"Error extracting system ID: {e}")
            return None
    
    def _save_results(self):
        """Save results to JSON files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save feeds
        with open(f"{self.output_dir}/feeds_{timestamp}.json", 'w') as f:
            feed_dicts = [feed.to_dict() for feed in self.feeds]
            json.dump(feed_dicts, f, indent=2)
        
        # Save systems
        with open(f"{self.output_dir}/systems_{timestamp}.json", 'w') as f:
            json.dump({
                str(sid): system.to_dict()
                for sid, system in self.systems.items()
            }, f, indent=2)
        
        # Save talkgroups
        with open(f"{self.output_dir}/talkgroups_{timestamp}.json", 'w') as f:
            json.dump({
                str(sid): [tg.to_dict() for tg in tgs]
                for sid, tgs in self.talkgroups.items()
            }, f, indent=2)
        
        # Save recent calls
        with open(f"{self.output_dir}/recent_calls_{timestamp}.json", 'w') as f:
            json.dump({
                f"{sid}_{tgid}": [call.to_dict() for call in calls]
                for (sid, tgid), calls in self.recent_calls.items()
            }, f, indent=2)
    
    def _display_summary(self):
        """Display a colorful summary of what was found."""
        console.print("\n[bold cyan]Scraping Summary[/bold cyan]")
        
        # Create summary table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right", style="green")
        
        table.add_row("Feeds", str(len(self.feeds)))
        table.add_row("Systems", str(len(self.systems)))
        table.add_row(
            "Talkgroups",
            str(sum(len(tgs) for tgs in self.talkgroups.values()))
        )
        table.add_row(
            "Recent Calls",
            str(sum(len(calls) for calls in self.recent_calls.values()))
        )
        
        console.print(table)
        
        # Show output location
        console.print(
            f"\nResults saved in: [bold yellow]{self.output_dir}/[/bold yellow]"
        )

@click.command()
@click.argument('state')
@click.option(
    '--username', '-u',
    envvar='BROADCASTIFY_USERNAME',
    help='Broadcastify username'
)
@click.option(
    '--password', '-p',
    envvar='BROADCASTIFY_PASSWORD',
    help='Broadcastify password'
)
@click.option(
    '--output', '-o',
    default='output',
    help='Output directory'
)
@click.option('--debug/--no-debug', default=False, help='Enable debug logging')
def main(state: str, username: str, password: str, output: str, debug: bool):
    """Scrape all Broadcastify data for a STATE."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('broadcastify').setLevel(logging.DEBUG)
    
    if not username or not password:
        # Try to load from login.txt
        try:
            with open('login.txt') as f:
                username, password = f.read().strip().split(':')
        except Exception:
            console.print(
                "[red]Error: Please provide credentials via options "
                "or in login.txt[/red]"
            )
            sys.exit(1)
    
    scraper = StateScraper(username, password, output)
    try:
        scraper.scrape_state(state)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scraping interrupted![/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

if __name__ == '__main__':
    main()
