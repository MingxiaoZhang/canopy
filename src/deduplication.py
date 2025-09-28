import hashlib
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Set, Dict, Optional, Tuple
import logging
from collections import defaultdict
import time

class BloomFilter:
    """Memory-efficient probabilistic data structure for duplicate detection"""

    def __init__(self, capacity: int = 1000000, error_rate: float = 0.1):
        """
        Initialize Bloom filter

        Args:
            capacity: Expected number of items
            error_rate: Acceptable false positive rate
        """
        self.capacity = capacity
        self.error_rate = error_rate

        # Calculate optimal parameters
        self.bit_array_size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        self.hash_count = int(self.bit_array_size * math.log(2) / capacity)

        # Initialize bit array
        self.bit_array = [False] * self.bit_array_size
        self.item_count = 0

    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for given item and seed"""
        hash_obj = hashlib.md5((item + str(seed)).encode())
        return int(hash_obj.hexdigest(), 16) % self.bit_array_size

    def add(self, item: str):
        """Add item to bloom filter"""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            self.bit_array[index] = True
        self.item_count += 1

    def __contains__(self, item: str) -> bool:
        """Check if item might be in the set"""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            if not self.bit_array[index]:
                return False
        return True

# Simple Bloom filter without math import for compatibility
class SimpleBloomFilter:
    """Simplified bloom filter implementation"""

    def __init__(self, capacity: int = 100000):
        self.capacity = capacity
        self.bit_array = [False] * (capacity * 10)  # 10x size for lower collision rate
        self.item_count = 0

    def _hash(self, item: str, seed: int) -> int:
        """Simple hash function"""
        hash_value = hash(item + str(seed))
        return abs(hash_value) % len(self.bit_array)

    def add(self, item: str):
        """Add item to bloom filter"""
        for seed in range(3):  # Use 3 different hash functions
            index = self._hash(item, seed)
            self.bit_array[index] = True
        self.item_count += 1

    def __contains__(self, item: str) -> bool:
        """Check if item might be in the set"""
        for seed in range(3):
            index = self._hash(item, seed)
            if not self.bit_array[index]:
                return False
        return True

class URLCanonicalizer:
    """URL canonicalization and normalization"""

    def __init__(self):
        # Common tracking parameters to remove
        self.tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'msclkid', 'ref', 'referrer', '_ga', '_gid',
            'source', 'campaign', 'medium', 'content', 'term',
            'igshid', 'ncid', 'sr_share', 'recruiter', 'trk'
        }

        # Parameters that should be kept and normalized
        self.meaningful_params = {
            'id', 'page', 'p', 'offset', 'limit', 'sort', 'order',
            'category', 'tag', 'search', 'q', 'query', 'filter'
        }

    def canonicalize(self, url: str) -> str:
        """
        Canonicalize URL to standard form

        Args:
            url: Raw URL to canonicalize

        Returns:
            Canonicalized URL string
        """
        try:
            parsed = urlparse(url.lower().strip())

            # Normalize scheme
            if not parsed.scheme:
                parsed = urlparse(f"https://{url}")

            # Normalize domain (remove www, convert to lowercase)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            # Normalize path (remove trailing slash, decode percent encoding)
            path = parsed.path.rstrip('/')
            if not path:
                path = '/'

            # Filter and sort query parameters
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=False)

                # Remove tracking parameters
                filtered_params = {
                    k: v for k, v in params.items()
                    if k.lower() not in self.tracking_params
                }

                # Sort parameters for consistency
                if filtered_params:
                    sorted_params = sorted(filtered_params.items())
                    query = urlencode(sorted_params, doseq=True)
                else:
                    query = ''
            else:
                query = ''

            # Remove fragment (everything after #)
            canonical_url = urlunparse((
                parsed.scheme,
                domain,
                path,
                '',  # params
                query,
                ''   # fragment
            ))

            return canonical_url

        except Exception as e:
            logging.warning(f"Failed to canonicalize URL {url}: {e}")
            return url.lower().strip()

    def is_equivalent(self, url1: str, url2: str) -> bool:
        """Check if two URLs are equivalent after canonicalization"""
        return self.canonicalize(url1) == self.canonicalize(url2)

class ContentHasher:
    """Content-based deduplication using hashing"""

    def __init__(self):
        self.content_hashes: Dict[str, str] = {}  # hash -> first_url
        self.url_to_hash: Dict[str, str] = {}     # url -> content_hash

    def hash_content(self, content: str, content_type: str = 'html') -> str:
        """
        Generate hash for content

        Args:
            content: Content to hash
            content_type: Type of content (html, css, etc.)

        Returns:
            SHA-256 hash of content
        """
        if content_type == 'html':
            # For HTML, normalize whitespace and remove dynamic elements
            normalized = self._normalize_html(content)
        else:
            # For other content types, use as-is
            normalized = content

        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _normalize_html(self, html: str) -> str:
        """Normalize HTML for consistent hashing"""
        # Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

        # Remove script tags (often contain timestamps)
        html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove common dynamic elements
        dynamic_patterns = [
            r'timestamp["\']?\s*:\s*["\']?\d+["\']?',
            r'_token["\']?\s*:\s*["\'][^"\']+["\']',
            r'csrfToken["\']?\s*:\s*["\'][^"\']+["\']',
            r'sessionId["\']?\s*:\s*["\'][^"\']+["\']',
        ]

        for pattern in dynamic_patterns:
            html = re.sub(pattern, '', html, flags=re.IGNORECASE)

        # Normalize whitespace
        html = re.sub(r'\s+', ' ', html)

        return html.strip()

    def is_duplicate_content(self, content: str, url: str, content_type: str = 'html') -> Tuple[bool, Optional[str]]:
        """
        Check if content is duplicate

        Args:
            content: Content to check
            url: URL of the content
            content_type: Type of content

        Returns:
            (is_duplicate, original_url_if_duplicate)
        """
        content_hash = self.hash_content(content, content_type)

        if content_hash in self.content_hashes:
            original_url = self.content_hashes[content_hash]
            return True, original_url
        else:
            # Store this content hash
            self.content_hashes[content_hash] = url
            self.url_to_hash[url] = content_hash
            return False, None

    def get_stats(self) -> Dict[str, int]:
        """Get deduplication statistics"""
        return {
            'unique_content_hashes': len(self.content_hashes),
            'total_urls_processed': len(self.url_to_hash)
        }

class DuplicationManager:
    """Main deduplication system combining URL and content deduplication"""

    def __init__(self, use_bloom_filter: bool = True, bloom_capacity: int = 100000):
        self.url_canonicalizer = URLCanonicalizer()
        self.content_hasher = ContentHasher()

        # URL tracking
        self.seen_urls: Set[str] = set()
        self.canonical_to_original: Dict[str, str] = {}

        # Bloom filter for memory efficiency
        self.use_bloom_filter = use_bloom_filter
        if use_bloom_filter:
            self.url_bloom = SimpleBloomFilter(bloom_capacity)

        # Statistics
        self.stats = {
            'urls_processed': 0,
            'duplicate_urls': 0,
            'duplicate_content': 0,
            'canonical_urls': 0
        }

    def is_duplicate_url(self, url: str) -> Tuple[bool, str]:
        """
        Check if URL is duplicate

        Args:
            url: URL to check

        Returns:
            (is_duplicate, canonical_url)
        """
        canonical_url = self.url_canonicalizer.canonicalize(url)
        self.stats['urls_processed'] += 1

        # Check bloom filter first (if enabled)
        if self.use_bloom_filter:
            if canonical_url in self.url_bloom:
                # Might be duplicate, check definitive set
                if canonical_url in self.seen_urls:
                    self.stats['duplicate_urls'] += 1
                    return True, canonical_url
            else:
                # Definitely not seen before
                self.url_bloom.add(canonical_url)
                self.seen_urls.add(canonical_url)
                self.canonical_to_original[canonical_url] = url
                self.stats['canonical_urls'] += 1
                return False, canonical_url

        # Direct set check (fallback or if bloom filter disabled)
        if canonical_url in self.seen_urls:
            self.stats['duplicate_urls'] += 1
            return True, canonical_url
        else:
            self.seen_urls.add(canonical_url)
            self.canonical_to_original[canonical_url] = url
            self.stats['canonical_urls'] += 1
            if self.use_bloom_filter:
                self.url_bloom.add(canonical_url)
            return False, canonical_url

    def is_duplicate_content(self, content: str, url: str, content_type: str = 'html') -> Tuple[bool, Optional[str]]:
        """
        Check if content is duplicate

        Args:
            content: Content to check
            url: URL of the content
            content_type: Type of content

        Returns:
            (is_duplicate, original_url_if_duplicate)
        """
        is_dup, original_url = self.content_hasher.is_duplicate_content(content, url, content_type)
        if is_dup:
            self.stats['duplicate_content'] += 1
        return is_dup, original_url

    def should_crawl(self, url: str) -> Tuple[bool, str, str]:
        """
        Determine if URL should be crawled

        Args:
            url: URL to check

        Returns:
            (should_crawl, canonical_url, reason)
        """
        is_dup_url, canonical_url = self.is_duplicate_url(url)

        if is_dup_url:
            original_url = self.canonical_to_original.get(canonical_url, canonical_url)
            return False, canonical_url, f"Duplicate URL (canonical: {canonical_url}, original: {original_url})"

        return True, canonical_url, "New URL"

    def get_deduplication_stats(self) -> Dict[str, any]:
        """Get comprehensive deduplication statistics"""
        content_stats = self.content_hasher.get_stats()

        return {
            'url_stats': self.stats.copy(),
            'content_stats': content_stats,
            'efficiency': {
                'url_dedup_rate': self.stats['duplicate_urls'] / max(self.stats['urls_processed'], 1) * 100,
                'content_dedup_rate': self.stats['duplicate_content'] / max(content_stats['total_urls_processed'], 1) * 100,
                'total_urls_seen': len(self.seen_urls),
                'bloom_filter_enabled': self.use_bloom_filter
            }
        }

    def clear_old_entries(self, max_age_hours: float = 24):
        """Clear old entries to prevent unbounded memory growth"""
        # This is a simplified version - in production, you'd want timestamped entries
        if len(self.seen_urls) > 50000:  # Arbitrary threshold
            logging.info("Clearing old URL entries to prevent memory issues")
            # Keep only the most recent entries (this is simplified)
            recent_urls = list(self.seen_urls)[-25000:]  # Keep half
            self.seen_urls = set(recent_urls)

            # Rebuild canonical mapping
            self.canonical_to_original = {
                url: url for url in recent_urls
            }

            # Reset bloom filter
            if self.use_bloom_filter:
                self.url_bloom = SimpleBloomFilter(100000)
                for url in recent_urls:
                    self.url_bloom.add(url)