"""
Crawler Builder - Fluent API for building crawlers with features
"""

from typing import List
from .base import BaseCrawler
from ..features.screenshot_feature import ScreenshotFeature
from ..features.dom_extraction_feature import DOMExtractionFeature
from ..features.graph_crawling_feature import GraphCrawlingFeature


class CrawlerBuilder:
    """Builder for creating crawlers with various features"""

    def __init__(self, start_urls: List[str]):
        self.start_urls = start_urls
        self._max_pages = 100
        self.features = []

    def max_pages(self, count: int):
        """Set maximum pages to crawl"""
        self._max_pages = count
        return self

    def with_screenshots(self, enable: bool = True):
        """Add screenshot capability"""
        if enable:
            self.features.append(ScreenshotFeature())
        return self

    def with_dom_extraction(self, enable: bool = True, max_depth: int = 8,
                           capture_screenshots: bool = True):
        """Add DOM extraction capability"""
        if enable:
            self.features.append(DOMExtractionFeature(
                max_depth=max_depth,
                capture_screenshots=capture_screenshots
            ))
        return self

    def with_graph_crawling(self, enable: bool = True, mode: str = "single_domain",
                           max_depth: int = 3, max_domains: int = 100,
                           allowed_domains=None, blocked_domains=None, priority_domains=None):
        """Add graph crawling capability"""
        if enable:
            self.features.append(GraphCrawlingFeature(
                mode=mode,
                max_depth=max_depth,
                max_domains=max_domains,
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                priority_domains=priority_domains
            ))
        return self

    def build(self) -> BaseCrawler:
        """Build the configured crawler"""
        crawler = BaseCrawler(self.start_urls, self._max_pages)

        # Add all configured features
        for feature in self.features:
            crawler.add_feature(feature)

        return crawler