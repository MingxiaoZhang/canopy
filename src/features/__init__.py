"""
Crawler Features - Composable features for the crawler
"""

from .base import CrawlerFeature
from .screenshot_feature import ScreenshotFeature
from .dom_extraction_feature import DOMExtractionFeature
from .graph_crawling_feature import GraphCrawlingFeature

__all__ = [
    'CrawlerFeature',
    'ScreenshotFeature',
    'DOMExtractionFeature',
    'GraphCrawlingFeature'
]