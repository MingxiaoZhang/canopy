"""
Crawler Features - Composable features for the crawler
"""

from .base import CrawlerFeature
from .screenshot_feature import ScreenshotFeature
from .dom_extraction_feature import DOMExtractionFeature
from .graph_crawling_feature import GraphCrawlingFeature
from .css_download_feature import CSSDownloadFeature

__all__ = [
    'CrawlerFeature',
    'ScreenshotFeature',
    'DOMExtractionFeature',
    'GraphCrawlingFeature',
    'CSSDownloadFeature'
]