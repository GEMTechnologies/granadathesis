#!/usr/bin/env python3
"""
Cache Service - SQLite-based caching for academic search results

Provides fast caching for search results to:
- Reduce API calls by 80%+
- Improve response time 10x
- Respect rate limits
- Enable offline access
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """SQLite-based cache for search results."""
    
    def __init__(self, cache_dir: str = "thesis_data/cache", ttl_days: int = 7):
        """
        Initialize cache service.
        
        Args:
            cache_dir: Directory for cache database
            ttl_days: Time-to-live for cached results in days
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "search_cache.db"
        self.ttl_days = ttl_days
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                filters TEXT,
                api_source TEXT,
                results TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1
            )
        """)
        
        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_query 
            ON cache(query, api_source)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON cache(created_at)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Cache database initialized at {self.db_path}")
    
    def _generate_cache_key(self, query: str, api_source: str, filters: Optional[Dict] = None) -> str:
        """
        Generate unique cache key.
        
        Args:
            query: Search query
            api_source: API name (e.g., 'semantic_scholar', 'openalex')
            filters: Optional filters dict
            
        Returns:
            MD5 hash as cache key
        """
        key_data = {
            "query": query.lower().strip(),
            "api": api_source,
            "filters": filters or {}
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, query: str, api_source: str, filters: Optional[Dict] = None) -> Optional[List[Dict]]:
        """
        Get cached results.
        
        Args:
            query: Search query
            api_source: API name
            filters: Optional filters
            
        Returns:
            Cached results or None if not found/expired
        """
        cache_key = self._generate_cache_key(query, api_source, filters)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get cached result
        cursor.execute("""
            SELECT results, created_at, access_count
            FROM cache
            WHERE cache_key = ?
        """, (cache_key,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        results_json, created_at, access_count = row
        
        # Check if expired
        created_dt = datetime.fromisoformat(created_at)
        if datetime.now() - created_dt > timedelta(days=self.ttl_days):
            # Expired - delete and return None
            cursor.execute("DELETE FROM cache WHERE cache_key = ?", (cache_key,))
            conn.commit()
            conn.close()
            logger.info(f"Cache expired for query: {query[:50]}...")
            return None
        
        # Update access stats
        cursor.execute("""
            UPDATE cache
            SET accessed_at = CURRENT_TIMESTAMP,
                access_count = ?
            WHERE cache_key = ?
        """, (access_count + 1, cache_key))
        
        conn.commit()
        conn.close()
        
        results = json.loads(results_json)
        logger.info(f"Cache HIT for query: {query[:50]}... (accessed {access_count + 1} times)")
        return results
    
    def set(self, query: str, api_source: str, results: List[Dict], filters: Optional[Dict] = None):
        """
        Cache search results.
        
        Args:
            query: Search query
            api_source: API name
            results: Search results to cache
            filters: Optional filters
        """
        cache_key = self._generate_cache_key(query, api_source, filters)
        results_json = json.dumps(results)
        filters_json = json.dumps(filters) if filters else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert or replace
        cursor.execute("""
            INSERT OR REPLACE INTO cache
            (cache_key, query, filters, api_source, results, created_at, accessed_at, access_count)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
        """, (cache_key, query, filters_json, api_source, results_json))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cache SET for query: {query[:50]}... ({len(results)} results)")
    
    def clear_expired(self):
        """Remove expired cache entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=self.ttl_days)
        
        cursor.execute("""
            DELETE FROM cache
            WHERE created_at < ?
        """, (cutoff_date.isoformat(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleared {deleted_count} expired cache entries")
        return deleted_count
    
    def clear_all(self):
        """Clear all cache entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM cache")
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cleared all {deleted_count} cache entries")
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total entries
        cursor.execute("SELECT COUNT(*) FROM cache")
        total_entries = cursor.fetchone()[0]
        
        # Total size
        cursor.execute("SELECT SUM(LENGTH(results)) FROM cache")
        total_size = cursor.fetchone()[0] or 0
        
        # Most accessed
        cursor.execute("""
            SELECT query, api_source, access_count
            FROM cache
            ORDER BY access_count DESC
            LIMIT 5
        """)
        most_accessed = cursor.fetchall()
        
        # By API
        cursor.execute("""
            SELECT api_source, COUNT(*), SUM(access_count)
            FROM cache
            GROUP BY api_source
        """)
        by_api = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "most_accessed": [
                {"query": q, "api": a, "count": c}
                for q, a, c in most_accessed
            ],
            "by_api": [
                {"api": a, "entries": e, "total_accesses": t}
                for a, e, t in by_api
            ]
        }


# Global cache instance
_cache_instance = None


def get_cache() -> CacheService:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance
