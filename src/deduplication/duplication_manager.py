import logging
from typing import Set, Dict, Optional, Tuple
from .url_canonicalizer import URLCanonicalizer
from .content_hasher import ContentHasher
from .simple_bloom_filter import SimpleBloomFilter


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