"""
Crawler Module - New Architecture Entry Point
Re-exports the new crawler architecture components
"""

# Export the new crawler architecture
from .crawler.base import BaseCrawler
from .crawler.builder import CrawlerBuilder
from .crawler.result import CrawlResult

# Export feature classes for advanced usage
from .features.screenshot_feature import ScreenshotFeature
from .features.dom_extraction_feature import DOMExtractionFeature
from .features.graph_crawling_feature import GraphCrawlingFeature

__all__ = [
    'BaseCrawler',
    'CrawlerBuilder',
    'CrawlResult',
    'ScreenshotFeature',
    'DOMExtractionFeature',
    'GraphCrawlingFeature'
]