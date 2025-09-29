"""
DOM Extraction Feature - Extracts DOM trees and component screenshots
"""

import logging
from typing import List, Optional
from .base import CrawlerFeature
from ..crawler.result import CrawlResult
from ..utils.dom_tree import DOMTreeExtractor


class DOMExtractionFeature(CrawlerFeature):
    """Feature for DOM tree extraction and component screenshots"""

    def __init__(self, max_depth: int = 8, capture_screenshots: bool = True,
                 screenshot_components: Optional[List[str]] = None):
        self.max_depth = max_depth
        self.capture_screenshots = capture_screenshots
        self.screenshot_components = screenshot_components
        self.dom_extractor = None

    async def initialize(self, crawler):
        """Initialize DOM extraction capability"""
        print(f"🌳 DOM extraction initialized (max_depth={self.max_depth})")

        # Initialize DOM tree extractor
        self.dom_extractor = DOMTreeExtractor()

    async def before_crawl(self, crawler):
        """Setup before crawling starts"""
        print("🌳 DOM extraction ready")

    async def process_url(self, url: str, result: CrawlResult, crawler):
        """Extract DOM tree for the given URL"""
        if not self.dom_extractor or not result.content:
            return

        try:
            # Find screenshot feature to get access to the page object
            screenshot_feature = None
            for feature in crawler.features:
                if hasattr(feature, 'page') and feature.page:
                    screenshot_feature = feature
                    break

            if screenshot_feature and screenshot_feature.page:
                page = screenshot_feature.page
                # Extract DOM tree using existing extractor
                dom_tree = await self.dom_extractor.extract_dom_tree(
                    page, url,
                    capture_screenshots=self.capture_screenshots,
                    max_depth=self.max_depth,
                    screenshot_components=self.screenshot_components
                )
                node_count = self.dom_extractor._count_nodes(dom_tree)
                print(f"🌳 DOM tree extracted with {node_count} nodes")

        except Exception as e:
            logging.warning(f"Failed to extract DOM tree for {url}: {e}")

    async def finalize(self, crawler):
        """Clean up DOM extraction resources"""
        print("🌳 DOM extraction cleaned up")