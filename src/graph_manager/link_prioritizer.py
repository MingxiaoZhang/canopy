import re
from urllib.parse import urlparse
from .graph_crawl_config import GraphCrawlConfig
from .link_info import LinkInfo
from .crawl_mode import CrawlMode


class LinkPrioritizer:
    """Prioritizes links for crawling based on various factors"""

    def __init__(self, config: GraphCrawlConfig):
        self.config = config

        # File extension priorities
        self.high_priority_extensions = {'.html', '.htm', '.php', '.asp', '.aspx', '.jsp', ''}
        self.medium_priority_extensions = {'.pdf', '.doc', '.docx', '.txt'}
        self.low_priority_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.css', '.js'}
        self.blocked_extensions = {'.zip', '.exe', '.dmg', '.iso', '.tar', '.gz'}

        # URL pattern priorities
        self.high_priority_patterns = [
            r'/blog/', r'/news/', r'/article/', r'/post/', r'/content/',
            r'/research/', r'/publications/', r'/papers/', r'/docs/'
        ]
        self.low_priority_patterns = [
            r'/admin/', r'/login/', r'/register/', r'/cart/', r'/checkout/',
            r'/api/', r'/ajax/', r'/json/', r'/xml/'
        ]

    def calculate_priority(self, link_info: LinkInfo, page_content: str = "") -> int:
        """Calculate priority score for a link"""
        priority = 100  # Base priority
        url = link_info.url.lower()
        domain = link_info.domain.lower()

        # Domain-based scoring
        if domain in self.config.priority_domains:
            priority += 200
        elif domain in self.config.allowed_domains and self.config.mode == CrawlMode.WHITELIST:
            priority += 100
        elif domain in self.config.blocked_domains:
            return -1000  # Block completely

        # Same domain bonus
        source_domain = urlparse(link_info.source_url).netloc.lower()
        if domain == source_domain:
            priority += 150

        # Depth penalty
        priority -= (link_info.depth * 50)

        # File extension scoring
        file_ext = self._get_file_extension(url)
        if file_ext in self.blocked_extensions:
            return -1000
        elif file_ext in self.high_priority_extensions:
            priority += 50
        elif file_ext in self.medium_priority_extensions:
            priority += 20
        elif file_ext in self.low_priority_extensions:
            priority -= 30

        # URL pattern scoring
        for pattern in self.high_priority_patterns:
            if re.search(pattern, url):
                priority += 30
                break

        for pattern in self.low_priority_patterns:
            if re.search(pattern, url):
                priority -= 50
                break

        # Link text scoring
        if link_info.link_text:
            text_lower = link_info.link_text.lower()
            if any(keyword in text_lower for keyword in ['article', 'blog', 'news', 'read more']):
                priority += 25
            if any(keyword in text_lower for keyword in ['login', 'register', 'cart', 'buy now']):
                priority -= 25

        # Keyword filtering
        if self.config.keyword_filters and page_content:
            content_lower = page_content.lower()
            keyword_matches = sum(1 for keyword in self.config.keyword_filters if keyword.lower() in content_lower)
            if keyword_matches > 0:
                priority += (keyword_matches * 25)

        return max(priority, 0)

    def _get_file_extension(self, url: str) -> str:
        """Extract file extension from URL"""
        path = urlparse(url).path
        if '.' in path:
            return path.split('.')[-1].lower()
        return ''