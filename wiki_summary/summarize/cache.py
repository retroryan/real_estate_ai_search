"""
Simple file-based caching for DSPy summarization results.
Provides cost-effective development and demo functionality.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Any
import logging
from wiki_summary.exceptions import FileReadException

logger = logging.getLogger(__name__)


class SummaryCache:
    """
    Simple file-based cache for Wikipedia summaries.
    Uses MD5 hash of input content for cache keys.
    """
    
    def __init__(self, cache_dir: str = ".cache/summaries"):
        """
        Initialize the cache with a directory.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized cache at {self.cache_dir}")
    
    def get_cache_key(self, page_id: int, content: str) -> str:
        """
        Generate cache key from page ID and content hash.
        
        Args:
            page_id: Wikipedia page ID
            content: Page content for hashing
            
        Returns:
            Cache key string
        """
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"{page_id}_{content_hash}"
    
    def get(self, page_id: int, content: str) -> Optional[dict]:
        """
        Retrieve cached summary if available.
        
        Args:
            page_id: Wikipedia page ID
            content: Page content for cache key
            
        Returns:
            Cached summary data or None if not found
        """
        cache_key = self.get_cache_key(page_id, content)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    logger.debug(f"Cache hit for page {page_id}")
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache for {page_id}: {e}")
        
        return None
    
    def set(self, page_id: int, content: str, summary_data: dict) -> bool:
        """
        Store summary in cache.
        
        Args:
            page_id: Wikipedia page ID
            content: Page content for cache key
            summary_data: Summary data to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        cache_key = self.get_cache_key(page_id, content)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
            logger.debug(f"Cached summary for page {page_id}")
            return True
        except (IOError, OSError) as e:
            logger.error(f"Failed to cache summary for {page_id}: {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize summary for {page_id}: {e}")
            return False
    
    def clear(self) -> int:
        """
        Clear all cached summaries.
        
        Returns:
            Number of cache files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except (IOError, OSError) as e:
                logger.warning(f"Failed to delete {cache_file}: {e}")
        
        logger.info(f"Cleared {count} cache files")
        return count
    
    def stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "cache_dir": str(self.cache_dir),
            "num_cached": len(cache_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "avg_size_kb": round(total_size / len(cache_files) / 1024, 2) if cache_files else 0
        }