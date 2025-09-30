"""
Graph Crawling Feature - Intelligent link discovery and graph-based crawling
"""

import logging
from typing import Set, Optional
from ..graph_manager import GraphCrawlManager, GraphCrawlConfig, CrawlMode
from .base import CrawlerFeature
from ..crawler.result import CrawlResult

logger = logging.getLogger(__name__)


class GraphCrawlingFeature(CrawlerFeature):
    """Feature for graph-based crawling with intelligent link discovery"""

    def __init__(self,
                 mode: str = "single_domain",
                 max_depth: int = 3,
                 max_domains: int = 100,
                 allowed_domains: Optional[Set[str]] = None,
                 blocked_domains: Optional[Set[str]] = None,
                 priority_domains: Optional[Set[str]] = None):

        # Convert string mode to enum
        mode_map = {
            "single_domain": CrawlMode.SINGLE_DOMAIN,
            "cross_domain": CrawlMode.CROSS_DOMAIN,
            "whitelist": CrawlMode.WHITELIST,
            "graph": CrawlMode.GRAPH,
            "focused": CrawlMode.FOCUSED
        }

        # Create graph crawl configuration
        self.config = GraphCrawlConfig(
            mode=mode_map.get(mode, CrawlMode.SINGLE_DOMAIN),
            max_depth=max_depth,
            max_domains=max_domains,
            allowed_domains=allowed_domains or set(),
            blocked_domains=blocked_domains or set(),
            priority_domains=priority_domains or set()
        )

        self.graph_manager = None
        self.discovered_links = []

    async def initialize(self, crawler):
        """Initialize graph crawling capability"""
        logger.info(f"Graph crawling initialized (mode={self.config.mode.value}, max_depth={self.config.max_depth})")

        # Initialize the graph crawl manager
        self.graph_manager = GraphCrawlManager(self.config)

        # Initialize with the crawler's start URLs
        if hasattr(crawler, 'start_urls'):
            self.graph_manager.initialize_seeds(crawler.start_urls)

    async def before_crawl(self, crawler):
        """Setup before crawling starts"""
        logger.info("Graph crawling ready")

    async def process_url(self, url: str, result: CrawlResult, crawler):
        """Analyze links and update crawling graph"""
        if not self.graph_manager or not result.parsed_data:
            return

        # Extract links from the current page
        if 'links' in result.parsed_data:
            discovered_links = self.graph_manager.extract_links_from_page(
                url, result.parsed_data, result.content or ""
            )

            if discovered_links:
                logger.info(f"Discovered {len(discovered_links)} links from {url}")

                # Add discovered links to crawler's queue
                for link in discovered_links:
                    crawler.add_url_to_queue(link.url, priority=link.priority)

                # Show high-priority links
                high_priority_links = [
                    link for link in discovered_links
                    if link.priority > 150  # High priority threshold
                ]

                if high_priority_links:
                    logger.debug(f"Found {len(high_priority_links)} high-priority links")

                # Store for statistics
                self.discovered_links.extend(discovered_links)

    async def finalize(self, crawler):
        """Clean up graph crawling resources and show statistics"""
        if self.graph_manager:
            logger.info("Graph crawling statistics:")
            logger.info(f"  Discovered domains: {len(self.graph_manager.discovered_domains)}")
            logger.info(f"  Total links discovered: {len(self.discovered_links)}")

            if self.discovered_links:
                # Show top domains
                domain_counts = {}
                for link in self.discovered_links:
                    domain_counts[link.domain] = domain_counts.get(link.domain, 0) + 1

                top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                logger.info(f"  Top discovered domains: {[f'{d}({c})' for d, c in top_domains]}")

                # Show some example links
                logger.info("  Example links discovered:")
                for link in self.discovered_links[:3]:
                    logger.info(f"    - {link.url} (priority: {link.priority})")

        logger.info("Graph crawling completed")