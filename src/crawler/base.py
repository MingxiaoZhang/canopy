"""
Base Crawler - Core crawling functionality with composable features
"""

import aiohttp
import time
import logging
from typing import List
from ..features.base import CrawlerFeature
from .result import CrawlResult
from ..utils.parser import HTMLParser
from ..storage import FileStorage, ContentType
from ..utils.rate_limiter import RateLimiter
from ..deduplication import DuplicationManager
from ..monitoring import MetricsCollector, ProgressReporter, LogManager

logger = logging.getLogger(__name__)


class BaseCrawler:
    """
    Clean base crawler focused on core crawling logic
    Features are added via composition using the builder pattern
    Built-in capabilities: rate limiting, deduplication, monitoring
    """

    def __init__(self, start_urls: List[str], max_pages: int = 100):
        self.start_urls = start_urls
        self.max_pages = max_pages
        self.features: List[CrawlerFeature] = []
        self.visited = set()
        self.pages_crawled = 0
        self.session = None
        self.storage = FileStorage()

        # Built-in logging
        self.log_manager = LogManager(log_dir="crawl_data/logs", log_level="INFO")

        # Built-in rate limiting (1s delay, respect robots.txt)
        self.rate_limiter = RateLimiter(default_delay=1.0)

        # Built-in deduplication
        self.deduplication_manager = DuplicationManager()

        # Built-in monitoring (30s report interval)
        self.metrics_collector = MetricsCollector()
        self.progress_reporter = ProgressReporter(self.metrics_collector, report_interval=30.0)

    def add_feature(self, feature: CrawlerFeature):
        """Add a feature to this crawler"""
        self.features.append(feature)
        return self

    async def crawl(self) -> None:
        """Main crawling workflow"""
        async with aiohttp.ClientSession() as session:
            self.session = session

            # Initialize rate limiter with robots.txt
            for url in self.start_urls:
                domain = self.rate_limiter.get_domain(url)
                await self.rate_limiter.initialize_domain(session, domain)

            # Start monitoring
            if self.progress_reporter:
                await self.progress_reporter.start_reporting()

            # Initialize all features
            for feature in self.features:
                await feature.initialize(self)

            # Notify features that crawling is starting
            for feature in self.features:
                await feature.before_crawl(self)

            try:
                # Main crawling loop
                await self._crawl_loop()
            finally:
                # Stop monitoring
                if self.progress_reporter:
                    await self.progress_reporter.stop_reporting()
                    self.progress_reporter.print_progress_report()

                    # Export final metrics
                    final_report = self.progress_reporter.get_final_report()
                    self.log_manager.export_metrics_json(final_report, "final_crawl_metrics.json")

                # Clean up all features
                for feature in self.features:
                    await feature.finalize(self)

    async def _crawl_loop(self):
        """Core crawling loop with real HTTP fetching"""
        for url in self.start_urls:
            if self.pages_crawled >= self.max_pages:
                break

            # Check deduplication
            if self.deduplication_manager:
                should_crawl, canonical_url, reason = self.deduplication_manager.should_crawl(url)
                if not should_crawl:
                    logger.info(f"Skipping duplicate URL: {url} - {reason}")
                    if self.metrics_collector:
                        self.metrics_collector.record_duplicate_skipped(url)
                    continue

            # Check rate limiting
            can_crawl, reason = await self.rate_limiter.can_crawl_url(url)
            if not can_crawl:
                logger.warning(f"Cannot crawl {url}: {reason}")
                if self.metrics_collector:
                    self.metrics_collector.record_error(url, reason)
                continue

            # Wait for rate limit
            await self.rate_limiter.wait_for_rate_limit(url)

            # Fetch real content
            result = await self._fetch_url(url)

            # Check content deduplication
            if result.content and self.deduplication_manager:
                is_dup, original_url = self.deduplication_manager.is_duplicate_content(
                    result.content, url, 'html'
                )
                if is_dup:
                    logger.info(f"Skipping duplicate content: {url} (same as {original_url})")
                    if self.metrics_collector:
                        self.metrics_collector.record_duplicate_skipped(url)
                    continue

            # Record metrics
            if self.metrics_collector and result.status_code == 200:
                content_length = len(result.content) if result.content else 0
                self.metrics_collector.record_page_crawled(
                    url, result.response_time, result.status_code, content_length
                )
            elif self.metrics_collector and result.error:
                self.metrics_collector.record_error(url, result.error, result.status_code)

            # Let features process the result
            for feature in self.features:
                await feature.process_url(url, result, self)

            self.visited.add(url)
            self.pages_crawled += 1
            logger.info(f"Crawled ({self.pages_crawled}/{self.max_pages}): {url}")

    async def _fetch_url(self, url: str) -> CrawlResult:
        """Fetch a single URL and return the result"""
        start_time = time.time()

        try:
            headers = {'User-Agent': 'TarzanCrawler/2.0'}
            timeout = aiohttp.ClientTimeout(total=30)

            async with self.session.get(url, headers=headers, timeout=timeout) as response:
                response_time = time.time() - start_time

                # Notify rate limiter of completed request
                await self.rate_limiter.request_completed(url, response_time, response.status)

                if response.status == 200:
                    content = await response.text()

                    # Parse HTML content
                    parser = HTMLParser(url)
                    parsed_data = parser.parse(content)

                    # Save HTML content
                    await self.storage.save_content(url, content, ContentType.HTML)

                    # Save inline CSS if present
                    if parsed_data.get('inline_css'):
                        # Join all CSS blocks into a single string
                        css_content = '\n\n'.join(parsed_data['inline_css'])
                        await self.storage.save_content(url, css_content, ContentType.CSS)

                    return CrawlResult(
                        url=url,
                        content=content,
                        parsed_data=parsed_data,
                        response_time=response_time,
                        status_code=response.status
                    )
                else:
                    return CrawlResult(
                        url=url,
                        error=f"HTTP {response.status}",
                        response_time=response_time,
                        status_code=response.status
                    )

        except Exception as e:
            response_time = time.time() - start_time
            # Notify rate limiter even on error
            await self.rate_limiter.request_completed(url, response_time, 0)
            return CrawlResult(
                url=url,
                error=str(e),
                response_time=response_time
            )