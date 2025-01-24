"""
Data models for the Broadcastify API.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class Feed:
    """Represents a Broadcastify feed."""
    id: int
    name: str
    description: str
    location: str
    status: str
    listeners: int = 0
    
    def to_dict(self) -> Dict:
        """Convert feed to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'status': self.status,
            'listeners': self.listeners
        }

@dataclass
class MetroFeed(Feed):
    """Represents a Broadcastify metro area feed."""
    metro_area_id: int
    
    def to_dict(self) -> Dict:
        """Convert feed to dictionary for JSON serialization."""
        return {
            **super().to_dict(),
            'metro_area_id': self.metro_area_id
        }

@dataclass
class System:
    """Represents a radio system."""
    id: int
    name: str
    type: str
    description: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description
        }

@dataclass
class Talkgroup:
    """Represents a talkgroup within a system."""
    id: int
    system_id: int
    name: str
    description: str = ""
    alpha_tag: str = ""
    mode: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'system_id': self.system_id,
            'name': self.name,
            'description': self.description,
            'alpha_tag': self.alpha_tag,
            'mode': self.mode
        }

@dataclass
class Call:
    """Represents a call on a talkgroup."""
    id: int
    system_id: int
    talkgroup_id: int
    timestamp: str
    duration: int = 0
    source: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'system_id': self.system_id,
            'talkgroup_id': self.talkgroup_id,
            'timestamp': self.timestamp,
            'duration': self.duration,
            'source': self.source
        }
