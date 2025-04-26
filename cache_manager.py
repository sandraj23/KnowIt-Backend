# This file will cache the LLM responses to avoid redundant API calls.

import os
import json
import hashlib
from typing import Any, Dict


class CacheManager:
    """
    A simple cache manager to store and retrieve LLM responses based on a hash of the input content.
    """

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _hash_content(self, content: str) -> str:
        """Generate a hash for the given content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _get_cache_path(self, content_hash: str) -> str:
        """Get the path to the cache file based on the content hash."""
        return os.path.join(self.cache_dir, f"{content_hash}.json")

    def save_response(self, content: str, response: Dict[str, Any]):
        """Save the LLM response to the cache."""
        content_hash = self._hash_content(content)
        cache_path = self._get_cache_path(content_hash)
        
        with open(cache_path, 'w') as f:
            json.dump(response, f)

    def load_response(self, content: str) -> Dict[str, Any]:
        """Load the LLM response from the cache if it exists."""
        content_hash = self._hash_content(content)
        cache_path = self._get_cache_path(content_hash)
        
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        
        return None