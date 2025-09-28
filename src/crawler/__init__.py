"""
New Crawler Architecture - Clean, composable crawler with builder pattern
"""

from .base import BaseCrawler
from .builder import CrawlerBuilder
from .result import CrawlResult

__all__ = ['BaseCrawler', 'CrawlerBuilder', 'CrawlResult']