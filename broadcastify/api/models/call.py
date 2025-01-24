"""Call model."""

from dataclasses import dataclass, asdict
from typing import Dict

@dataclass
class Call:
    """Represents a call on a talkgroup."""
    id: int
    system_id: int
    talkgroup_id: int
    timestamp: str
    description: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
