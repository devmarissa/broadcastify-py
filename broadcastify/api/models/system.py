"""System model."""

from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class System:
    """Represents a Broadcastify system."""
    id: int
    name: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
