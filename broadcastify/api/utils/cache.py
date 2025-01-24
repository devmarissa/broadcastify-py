"""
Caching functionality to reduce load on Broadcastify servers.
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

class Cache:
    """
    Simple file-based cache for API responses.
    
    This helps reduce load on the Broadcastify servers by caching responses
    locally. Different types of data have different expiration times.
    """
    
    def __init__(self, cache_dir: str = ".bc_cache"):
        self.cache_dir = cache_dir
        self.expiration = {
            "system": timedelta(days=7),    # System info rarely changes
            "talkgroup": timedelta(days=1),  # Talkgroup info might change daily
            "feed": timedelta(hours=1),      # Feed status changes frequently
            "call": timedelta(minutes=5),    # Call data very temporary
        }
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _get_path(self, key: str, data_type: str) -> str:
        """Get the full path for a cache file."""
        return os.path.join(self.cache_dir, f"{data_type}_{key}.pickle")
    
    def get(self, key: str, data_type: str = "default") -> Optional[Any]:
        """
        Retrieve an item from the cache.
        
        Args:
            key: Cache key
            data_type: Type of data being cached. Controls expiration time.
        
        Returns:
            The cached value if it exists and hasn't expired, None otherwise.
        """
        path = self._get_path(key, data_type)
        if not os.path.exists(path):
            return None
            
        try:
            with open(path, 'rb') as f:
                timestamp, data = pickle.load(f)
                
            # Check if expired
            age = datetime.now() - timestamp
            if age > self.expiration.get(data_type, timedelta(hours=1)):
                os.remove(path)
                return None
                
            return data
        except (pickle.UnpicklingError, EOFError):
            return None
    
    def set(self, key: str, value: Any, data_type: str = "default") -> None:
        """
        Store an item in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            data_type: Type of data being cached
        """
        path = self._get_path(key, data_type)
        with open(path, 'wb') as f:
            pickle.dump((datetime.now(), value), f)
