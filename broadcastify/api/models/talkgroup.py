"""Talkgroup model."""

from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class Talkgroup:
    """Represents a talkgroup in a system."""
    id: int
    system_id: int
    alpha: str
    description: str
    tag: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
