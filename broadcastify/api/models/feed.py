"""Feed models."""

from dataclasses import dataclass
from typing import Dict

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
    metro_area_id: int = 0  # Default value to satisfy dataclass requirements
    
    def __init__(self, id: int, name: str, description: str, location: str,
                 status: str, listeners: int = 0, metro_area_id: int = 0):
        """Initialize a metro feed."""
        super().__init__(id, name, description, location, status, listeners)
        self.metro_area_id = metro_area_id
    
    def to_dict(self) -> Dict:
        """Convert feed to dictionary for JSON serialization."""
        base_dict = super().to_dict()
        base_dict['metro_area_id'] = self.metro_area_id
        return base_dict
