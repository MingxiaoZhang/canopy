from dataclasses import dataclass
from typing import Set, List
from .crawl_mode import CrawlMode


@dataclass
class GraphCrawlConfig:
    """Configuration for graph-based crawling"""
    mode: CrawlMode = CrawlMode.SINGLE_DOMAIN
    max_depth: int = 3
    max_domains: int = 100
    allowed_domains: Set[str] = None
    blocked_domains: Set[str] = None
    priority_domains: Set[str] = None
    keyword_filters: List[str] = None
    file_type_filters: Set[str] = None
    min_domain_score: float = 0.1
    cross_domain_delay_multiplier: float = 2.0

    def __post_init__(self):
        if self.allowed_domains is None:
            self.allowed_domains = set()
        if self.blocked_domains is None:
            self.blocked_domains = set()
        if self.priority_domains is None:
            self.priority_domains = set()
        if self.keyword_filters is None:
            self.keyword_filters = []
        if self.file_type_filters is None:
            self.file_type_filters = {'.html', '.htm', '.php', '.asp', '.aspx', '.jsp', ''}