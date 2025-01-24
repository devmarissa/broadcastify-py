"""Coverage models."""

from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class TalkgroupCoverage:
    """Represents a talkgroup coverage entry."""
    id: int
    display: str
    description: str
    system: str
    last_seen: str
    system_id: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

@dataclass
class ServiceCoverage:
    """Represents coverage for a service type (Law, Fire, EMS)."""
    tag_id: int
    name: str  # e.g. "Law Dispatch", "Fire Dispatch"
    talkgroups: list[TalkgroupCoverage]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'tag_id': self.tag_id,
            'name': self.name,
            'talkgroups': [tg.to_dict() for tg in self.talkgroups]
        }
