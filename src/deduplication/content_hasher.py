import hashlib
import re
from typing import Dict, Optional, Tuple


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