"""
Search Utilities - Deduplication and Ranking

Provides:
- Result deduplication by URL/content similarity
- Result ranking by relevance/quality
- Diversity filtering to ensure varied results
"""

from typing import List, Dict, Any, Set
from urllib.parse import urlparse
import hashlib
from difflib import SequenceMatcher


def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings (0-1)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (remove query params, fragments)."""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".lower().rstrip('/')
    except:
        return url.lower()


def deduplicate_web_results(results: List[Dict[str, Any]], similarity_threshold: float = 0.85) -> List[Dict[str, Any]]:
    """
    Deduplicate web search results by URL and content similarity.
    
    Args:
        results: List of search result dicts with 'url', 'title', 'content'
        similarity_threshold: Minimum similarity to consider duplicates (0-1)
        
    Returns:
        Deduplicated list, keeping best result from each duplicate group
    """
    if not results:
        return []
    
    seen_urls: Set[str] = set()
    unique_results: List[Dict[str, Any]] = []
    
    for result in results:
        url = result.get('url', '')
        if not url:
            # Keep results without URLs (might be valuable)
            unique_results.append(result)
            continue
        
        normalized_url = normalize_url(url)
        
        # Check for exact URL match
        if normalized_url in seen_urls:
            continue
        
        # Check for similar URLs (same domain + similar path)
        is_duplicate = False
        for seen_url in seen_urls:
            if similarity(normalized_url, seen_url) > 0.9:
                is_duplicate = True
                break
        
        if is_duplicate:
            continue
        
        # Check for content similarity with existing results
        title = result.get('title', '').lower()
        content = result.get('content', '').lower()[:200]  # First 200 chars
        
        is_content_duplicate = False
        for existing in unique_results:
            existing_title = existing.get('title', '').lower()
            existing_content = existing.get('content', '').lower()[:200]
            
            # High title similarity
            if similarity(title, existing_title) > similarity_threshold:
                is_content_duplicate = True
                break
            
            # High content similarity
            if similarity(content, existing_content) > similarity_threshold:
                is_content_duplicate = True
                break
        
        if not is_content_duplicate:
            unique_results.append(result)
            seen_urls.add(normalized_url)
    
    return unique_results


def deduplicate_image_results(results: List[Dict[str, Any]], similarity_threshold: float = 0.85) -> List[Dict[str, Any]]:
    """
    Deduplicate image search results by URL and title similarity.
    
    Args:
        results: List of image result dicts with 'url', 'title', 'thumbnail'
        similarity_threshold: Minimum similarity to consider duplicates (0-1)
        
    Returns:
        Deduplicated list, keeping best result from each duplicate group
    """
    if not results:
        return []
    
    seen_urls: Set[str] = set()
    unique_results: List[Dict[str, Any]] = []
    
    for result in results:
        # Check full URL, thumbnail, and full image URL
        urls_to_check = [
            result.get('url', ''),
            result.get('thumbnail', ''),
            result.get('full', '')
        ]
        
        # Check if any URL is a duplicate
        is_duplicate = False
        for url in urls_to_check:
            if not url:
                continue
            
            normalized = normalize_url(url)
            if normalized in seen_urls:
                is_duplicate = True
                break
            
            # Check similarity with existing URLs
            for seen_url in seen_urls:
                if similarity(normalized, seen_url) > 0.9:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                break
        
        if is_duplicate:
            continue
        
        # Check title similarity
        title = result.get('title', '').lower()
        is_title_duplicate = False
        
        for existing in unique_results:
            existing_title = existing.get('title', '').lower()
            if similarity(title, existing_title) > similarity_threshold:
                is_title_duplicate = True
                break
        
        if not is_title_duplicate:
            unique_results.append(result)
            # Mark all URLs as seen
            for url in urls_to_check:
                if url:
                    seen_urls.add(normalize_url(url))
    
    return unique_results


def rank_web_results(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Rank web search results by relevance to query.
    
    Scoring factors:
    - Title match (highest weight)
    - Content match
    - URL domain authority (simple heuristic)
    
    Args:
        results: List of search result dicts
        query: Search query
        
    Returns:
        Ranked list (best first)
    """
    if not results:
        return []
    
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    scored_results = []
    for result in results:
        score = 0.0
        
        title = result.get('title', '').lower()
        content = result.get('content', '').lower()
        url = result.get('url', '').lower()
        
        # Title match (weight: 3.0)
        title_words = set(title.split())
        title_match = len(query_words & title_words) / max(len(query_words), 1)
        score += title_match * 3.0
        
        # Exact title match bonus
        if query_lower in title:
            score += 2.0
        
        # Content match (weight: 1.0)
        content_words = set(content.split()[:100])  # First 100 words
        content_match = len(query_words & content_words) / max(len(query_words), 1)
        score += content_match * 1.0
        
        # URL domain authority (simple heuristic)
        if any(domain in url for domain in ['edu', 'gov', 'org', 'wikipedia']):
            score += 0.5
        
        scored_results.append((score, result))
    
    # Sort by score (descending)
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    return [result for _, result in scored_results]


def rank_image_results(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Rank image search results by relevance and quality.
    
    Scoring factors:
    - Title/tags match
    - Image dimensions (larger = better)
    - Source quality (likes, views, downloads)
    
    Args:
        results: List of image result dicts
        query: Search query
        
    Returns:
        Ranked list (best first)
    """
    if not results:
        return []
    
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    scored_results = []
    for result in results:
        score = 0.0
        
        title = result.get('title', '').lower()
        tags = result.get('tags', '').lower() if isinstance(result.get('tags'), str) else ''
        
        # Title/tags match (weight: 3.0)
        title_words = set(title.split())
        if tags:
            title_words.update(tags.split())
        
        match_ratio = len(query_words & title_words) / max(len(query_words), 1)
        score += match_ratio * 3.0
        
        # Image quality (dimensions)
        width = result.get('width', 0) or 0
        height = result.get('height', 0) or 0
        if width > 0 and height > 0:
            # Prefer larger images (normalized to 0-1)
            size_score = min((width * height) / (1920 * 1080), 1.0)
            score += size_score * 1.0
        
        # Engagement metrics (if available)
        likes = result.get('likes', 0) or 0
        views = result.get('views', 0) or 0
        downloads = result.get('downloads', 0) or 0
        
        # Normalize engagement (assume max 1000 likes = 1.0)
        engagement = (likes / 1000.0) + (views / 10000.0) + (downloads / 500.0)
        score += min(engagement, 1.0) * 0.5
        
        scored_results.append((score, result))
    
    # Sort by score (descending)
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    return [result for _, result in scored_results]


def ensure_diversity(results: List[Dict[str, Any]], max_per_source: int = 3) -> List[Dict[str, Any]]:
    """
    Ensure result diversity by limiting results per source/domain.
    
    Args:
        results: List of results
        max_per_source: Maximum results per source/domain
        
    Returns:
        Diverse list of results
    """
    if not results:
        return []
    
    source_counts: Dict[str, int] = {}
    diverse_results: List[Dict[str, Any]] = []
    
    for result in results:
        # Determine source
        source = result.get('source', 'Unknown')
        url = result.get('url', '')
        
        # Try to get domain from URL
        if url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                source_key = domain or source
            except:
                source_key = source
        else:
            source_key = source
        
        # Check if we've reached limit for this source
        count = source_counts.get(source_key, 0)
        if count < max_per_source:
            diverse_results.append(result)
            source_counts[source_key] = count + 1
    
    return diverse_results




