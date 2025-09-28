"""
Base Feature Interface - Abstract base class for all crawler features
"""

from abc import ABC, abstractmethod
from ..crawler.result import CrawlResult


class CrawlerFeature(ABC):
    """Base interface for all crawler features"""

    @abstractmethod
    async def initialize(self, crawler) -> None:
        """Initialize the feature when crawler starts"""
        pass

    @abstractmethod
    async def before_crawl(self, crawler) -> None:
        """Called before crawling starts"""
        pass

    @abstractmethod
    async def process_url(self, url: str, result: CrawlResult, crawler) -> None:
        """Process a crawled URL result"""
        pass

    @abstractmethod
    async def finalize(self, crawler) -> None:
        """Clean up when crawling completes"""
        pass